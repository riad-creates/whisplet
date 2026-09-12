"""Experimental, bounded phrase boosting for the pinned Parakeet TDT decoder.

Only final batch transcription uses this path. Live streaming keeps the upstream
decoder and its cache unchanged. The TDT loop is adapted from parakeet-mlx 0.5.2
(Apache-2.0); see third_party/parakeet-mlx/LICENSE.
"""

from collections import deque
from dataclasses import dataclass, field
import json
import os
import re
from pathlib import Path


@dataclass
class Node:
    children: dict = field(default_factory=dict)
    failure: int = 0
    depth: int = 0


class PhraseBias:
    """Track token prefixes; shared prefixes never multiply the bonus."""

    def __init__(self, sequences, strength=1.5, terms=()):
        if not 0 <= strength <= 3:
            raise ValueError("dictionary strength must be between 0 and 3")
        self.strength = strength
        self.terms = tuple(terms)
        self.nodes = [Node()]
        for sequence in set(tuple(s) for s in sequences if s):
            current = 0
            for token in sequence:
                if token not in self.nodes[current].children:
                    self.nodes[current].children[token] = len(self.nodes)
                    self.nodes.append(Node(depth=self.nodes[current].depth + 1))
                current = self.nodes[current].children[token]
        pending = deque(self.nodes[0].children.values())
        while pending:
            parent = pending.popleft()
            for token, child in self.nodes[parent].children.items():
                fallback = self.nodes[parent].failure
                while fallback and token not in self.nodes[fallback].children:
                    fallback = self.nodes[fallback].failure
                self.nodes[child].failure = self.nodes[fallback].children.get(token, 0)
                pending.append(child)
        self._bonuses = {}

    def advance(self, state, token):
        while state and token not in self.nodes[state].children:
            state = self.nodes[state].failure
        return self.nodes[state].children.get(token, 0)

    def bonuses(self, state):
        if state not in self._bonuses:
            # A small start bonus, then a bounded continuation bonus. No bonus
            # accumulates across frames or duplicate dictionary entries.
            result = {token: self.strength * 0.25 for token in self.nodes[0].children}
            current = state
            while current:
                for token in self.nodes[current].children:
                    result[token] = self.strength
                current = self.nodes[current].failure
            self._bonuses[state] = result
        return self._bonuses[state]


def support_directory():
    return Path(os.environ.get("PHONON_DATA_DIR") or
                Path.home() / "Library/Application Support/Phonon")


def recognition_terms(directory):
    """Read a snapshot for this final pass. Never rewrite native settings."""
    settings_path = directory / "settings.json"
    settings = json.loads(settings_path.read_text()) if settings_path.exists() else {}
    if not isinstance(settings, dict):
        raise ValueError("settings must be an object")
    if settings.get("dictionary_recognition", True) is False:
        return []
    path = directory / "dictionary.json"
    data = json.loads(path.read_text()) if path.exists() else {}
    if (not isinstance(data, dict) or not isinstance(data.get("entries", []), list)
            or any(not isinstance(entry, dict) for entry in data.get("entries", []))):
        raise ValueError("dictionary must contain an entries list")
    # Replacement entries express text editing, not necessarily pronunciation:
    # "sign off" -> a full signature must not bias ASR toward that signature.
    return sorted({entry["phrase"].strip() for entry in data.get("entries", [])
                   if isinstance(entry.get("phrase"), str)
                   and entry["phrase"].strip() and not entry.get("replacement")})


def compile_bias(terms, tokenizer, vocabulary, strength=1.5):
    sequences = []
    for term in terms:
        for spelling in {term, term.lower()}:
            pieces = tokenizer.encode(spelling, out_type=str)
            ids = tokenizer.encode(spelling, out_type=int)
            if (not ids or tokenizer.unk_id() in ids or len(ids) != len(pieces)
                    or any(i >= len(vocabulary) or i < 0 or vocabulary[i] != piece
                           for i, piece in zip(ids, pieces))):
                raise ValueError(f"dictionary term cannot map to this model: {term!r}")
            sequences.append(ids)
    return PhraseBias(sequences, strength, terms) if sequences and strength else None


def restore_case(text, terms):
    """Restore spelling-case only, never turn 'phone on' into 'Phonon'."""
    for term in sorted(terms, key=len, reverse=True):
        text = re.sub(r"(?<!\w)" + re.escape(term) + r"(?!\w)",
                      lambda _: term, text, flags=re.IGNORECASE)
    return text


def generate_with_bias(model, mel, bias, *, compute_confidence=True, cache_decoder=False):
    """Use original audio logits; never boost blank or change duration logits.

    Text-only callers may skip confidence. Uncomputed token/sentence confidence
    is NaN, rather than a fabricated certainty. The upstream no-bias path is
    unchanged and still computes confidence.

    cache_decoder reuses the prediction network output after a blank, when its
    previous-token and hidden-state inputs are unchanged. Each emitted token
    invalidates it, including a repeat of the same token ID.
    """
    if bias is None:
        return model.generate(mel)
    import mlx.core as mx
    from parakeet_mlx.alignment import AlignedToken, sentences_to_result, tokens_to_sentences
    from parakeet_mlx.parakeet import ParakeetTDT, SentenceConfig
    from parakeet_mlx.tokenizer import decode

    if not isinstance(model, ParakeetTDT):
        raise ValueError("dictionary recognition currently requires Parakeet TDT")
    if len(mel.shape) == 2:
        mel = mx.expand_dims(mel, 0)
    features, lengths = model.encoder(mel)
    mx.eval(features, lengths)
    results = []
    blank = len(model.vocabulary)
    bonus_vectors = {}
    for batch in range(features.shape[0]):
        feature = features[batch:batch + 1]
        length = int(lengths[batch])
        step = symbols = state = 0
        previous = hidden_state = None
        decoder_out = next_hidden = None
        hypothesis = []
        while step < length:
            if not cache_decoder or decoder_out is None:
                decoder_out, (hidden, cell) = model.decoder(
                    mx.array([[previous]]) if previous is not None else None, hidden_state)
                decoder_out = decoder_out.astype(feature.dtype)
                next_hidden = (hidden.astype(feature.dtype), cell.astype(feature.dtype))
            joint = model.joint(feature[:, step:step + 1], decoder_out)
            logits = joint[0, 0, :, :blank + 1]
            original = int(mx.argmax(logits))
            chosen = original
            if original != blank:
                if state not in bonus_vectors:
                    vector = [0.0] * (blank + 1)
                    for token, bonus in bias.bonuses(state).items():
                        vector[token] = bonus
                    bonus_vectors[state] = mx.array(vector, dtype=mx.float32)
                chosen = int(mx.argmax(logits.astype(mx.float32) + bonus_vectors[state]))
            confidence = float("nan")
            if compute_confidence:
                # Confidence describes the original distribution, not boosted scores.
                probabilities = mx.softmax(logits.astype(mx.float32), axis=-1)
                entropy = -mx.sum(probabilities * mx.log(probabilities + 1e-10), axis=-1)
                confidence = float(1.0 - entropy / mx.log(mx.array(blank + 1)))
            duration_id = int(mx.argmax(joint[0, 0, :, blank + 1:]))
            duration = model.durations[duration_id]
            if chosen != blank:
                hypothesis.append(AlignedToken(
                    id=chosen, text=decode([chosen], model.vocabulary),
                    start=step * model.time_ratio, duration=duration * model.time_ratio,
                    confidence=confidence))
                previous = chosen
                hidden_state = next_hidden
                # A token changes recurrent state even if its ID is repeated.
                decoder_out = None
                state = bias.advance(state, chosen)
            step += duration
            symbols += 1
            if duration:
                symbols = 0
            elif model.max_symbols is not None and symbols >= model.max_symbols:
                step += 1
                symbols = 0
        results.append(sentences_to_result(tokens_to_sentences(hypothesis, SentenceConfig())))
    return results
