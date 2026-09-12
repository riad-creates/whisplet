"""Prediction cache state transitions, including blanks and repeated token IDs.

Tiny deterministic stand-ins keep this regression test independent of MLX/GPU
availability. Real-model transcript equivalence is checked by corpus replay.
"""
import sys
from types import SimpleNamespace

import numpy as np
import pytest

from sidecar.dictionary_bias import PhraseBias, generate_with_bias


@pytest.mark.parametrize('cache_decoder', [False, True])
def test_prediction_cache_preserves_recurrent_state_and_batch_boundaries(monkeypatch, cache_decoder):
    mx = SimpleNamespace(array=np.array, expand_dims=np.expand_dims,
                         argmax=np.argmax, float32=np.float32, eval=lambda *args: None)
    monkeypatch.setitem(sys.modules, 'mlx', SimpleNamespace(core=mx))
    monkeypatch.setitem(sys.modules, 'mlx.core', mx)

    class Model:
        vocabulary = [' a', ' b']
        durations = [0, 1]
        time_ratio = 0.08
        max_symbols = 2

        def __init__(self):
            self.decoder_calls = 0
            self.joint_calls = 0

        def encoder(self, mel):
            # Two utterances in one batch must have independent cached state.
            features = np.tile(np.arange(4, dtype=np.float32)[None, :, None], (2, 1, 1))
            return features, np.array([4, 4])

        def decoder(self, previous, hidden_state):
            self.decoder_calls += 1
            state = 0 if hidden_state is None else int(hidden_state[0].item())
            if state == 0:
                assert previous is None
            else:
                assert int(previous.item()) == 0  # The same token was repeated.
            value = np.array([[[state+1]]], dtype=np.float32)
            return value, (value, value)

        def joint(self, feature, prediction):
            index = self.joint_calls % 7
            self.joint_calls += 1
            # Initial blanks; repeated token; more blanks; final token.
            # Zero-duration steps exercise forced advancement via max_symbols.
            token = [2, 2, 0, 0, 2, 2, 1][index]
            duration_id = [0, 0, 0, 0, 0, 0, 1][index]
            assert int(prediction.item()) == [1, 1, 1, 2, 3, 3, 3][index]
            assert int(feature.item()) == [0, 0, 1, 1, 2, 2, 3][index]
            logits = np.zeros((1, 1, 1, 5), dtype=np.float32)
            logits[0, 0, 0, token] = 10
            logits[0, 0, 0, 3+duration_id] = 10
            return logits

    monkeypatch.setitem(sys.modules, 'parakeet_mlx', SimpleNamespace())
    monkeypatch.setitem(sys.modules, 'parakeet_mlx.parakeet',
                        SimpleNamespace(ParakeetTDT=Model, SentenceConfig=lambda: None))
    monkeypatch.setitem(sys.modules, 'parakeet_mlx.tokenizer',
                        SimpleNamespace(decode=lambda ids, vocab: ''.join(vocab[i] for i in ids)))
    monkeypatch.setitem(sys.modules, 'parakeet_mlx.alignment', SimpleNamespace(
        AlignedToken=SimpleNamespace,
        tokens_to_sentences=lambda tokens, config: tokens,
        sentences_to_result=lambda tokens: SimpleNamespace(
            text=''.join(t.text for t in tokens), tokens=tokens)))

    model = Model()
    bias = PhraseBias([[0, 1]])
    for _ in range(2):  # Nothing may leak into a later transcription either.
        results = generate_with_bias(model, np.zeros((4, 1)), bias,
                                     compute_confidence=False, cache_decoder=cache_decoder)
        assert [r.text for r in results] == [' a a b', ' a a b']
        for result in results:
            assert [t.id for t in result.tokens] == [0, 0, 1]
            assert [t.start for t in result.tokens] == [0.08, 0.08, 0.24]
            assert [t.duration for t in result.tokens] == [0, 0, 0.08]
    assert model.joint_calls == 28
    assert model.decoder_calls == (12 if cache_decoder else 28)
