#!/usr/bin/env python3
"""Offline replay of saved Phonon WAVs; never edits the app or original corpus.

Word disagreement is measured against the existing batch decoder, NOT a human
reference. Timing is measured computation plus simulated 400 ms arrivals, NOT
microphone-to-paste latency. Detailed transcripts stay in the ignored output.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def words(text):
    return re.findall(r"[\w]+(?:['’][\w]+)?", text.lower().replace('’', "'"))


def distance(a, b):
    row = list(range(len(b) + 1))
    for i, left in enumerate(a, 1):
        nxt = [i]
        for j, right in enumerate(b, 1):
            nxt.append(min(nxt[-1] + 1, row[j] + 1, row[j - 1] + (left != right)))
        row = nxt
    return row[-1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'target/streaming-reuse-2026-09-11')
    parser.add_argument('--id', action='append', default=[])
    parser.add_argument('--attention', choices=['local', 'original'], default='local')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    import mlx.core as mx
    import sentencepiece as spm
    from parakeet_mlx import from_pretrained
    from sidecar.asr_server import read_wav, transcribe_file
    from sidecar.dictionary_bias import compile_bias, recognition_terms, restore_case, support_directory

    source = Path.home()/'.cache/huggingface/hub/models--mlx-community--parakeet-tdt-0.6b-v2/snapshots/8ae155301e23d820d82aa60d24817c900e69e487'
    model = from_pretrained(str(source))
    mx.eval(model.parameters())
    terms = recognition_terms(support_directory())
    tok = spm.SentencePieceProcessor(model_file=str(source/'tokenizer.model'))
    bias = compile_bias(terms, tok, model.vocabulary)
    rate = model.preprocessor_config.sample_rate
    chunk = int(rate * 0.4)
    cases = []
    for p in sorted((support_directory()/'Corpus').glob('bar_*/metadata.json')):
        d = json.loads(p.read_text())
        if args.id and d['id'] not in args.id:
            continue
        if not d.get('speech_detected') or not d.get('raw_transcript'):
            continue
        wav = p.parent/d['audio_file']
        if wav.is_file():
            cases.append((d, wav))
    if not cases:
        raise SystemExit('No matching speech recordings')
    warm = ROOT/'assets/startup.wav'
    transcribe_file(model, str(warm), bias)
    warm_audio = read_wav(str(warm), rate)
    with model.transcribe_stream(context_size=(128,64), keep_original_attention=args.attention == 'original') as stream:
        for i in range(0, len(warm_audio), chunk):
            stream.add_audio(mx.array(warm_audio[i:i+chunk], dtype=mx.bfloat16))
        _ = stream.result.text

    rows = []
    for index, (meta, wav) in enumerate(cases, 1):
        digest = hashlib.sha256(wav.read_bytes()).hexdigest()
        samples = read_wav(str(wav), rate)
        duration = len(samples)/rate
        t = time.perf_counter()
        baseline = restore_case(transcribe_file(model, str(wav), bias).text, terms)
        batch_ms = (time.perf_counter()-t)*1000
        variants = {}
        virtual_done = 0.0
        chunk_ms = []
        with model.transcribe_stream(context_size=(128,64), keep_original_attention=args.attention == 'original') as stream:
            full_end = len(samples)//chunk*chunk
            for start in range(0, full_end, chunk):
                t = time.perf_counter()
                stream.add_audio(mx.array(samples[start:start+chunk], dtype=mx.bfloat16))
                current = stream.result.text
                elapsed = time.perf_counter()-t
                chunk_ms.append(elapsed*1000)
                virtual_done = max(virtual_done, (start+chunk)/rate) + elapsed
            variants['last_preview'] = {'text': stream.result.text.strip(),
                'estimated_after_release_ms': max(0,virtual_done-duration)*1000}
            t = time.perf_counter()
            tail = samples[full_end:]
            # End-of-stream flush includes every captured sample. A little
            # silence makes the final partial STFT/subsampling frame available.
            stream.add_audio(mx.concatenate([mx.array(tail, dtype=mx.bfloat16), mx.zeros((int(rate*0.24),),dtype=mx.bfloat16)]))
            text = stream.result.text.strip()
            flush_ms = (time.perf_counter()-t)*1000
            variants['flush_240ms'] = {'text': text, 'flush_compute_ms': flush_ms,
                'estimated_after_release_ms': max(0,virtual_done-duration)*1000 + flush_ms}
            t = time.perf_counter()
            stream.add_audio(mx.zeros((int(rate*0.4),),dtype=mx.bfloat16))
            text = stream.result.text.strip()
            extra_ms = (time.perf_counter()-t)*1000
            variants['flush_640ms'] = {'text': text, 'flush_compute_ms': flush_ms+extra_ms,
                'estimated_after_release_ms': max(0,virtual_done-duration)*1000 + flush_ms+extra_ms}
        for result in variants.values():
            result['text'] = restore_case(result['text'], terms)
            result['word_edits_vs_batch'] = distance(words(baseline), words(result['text']))
            result['same_words_as_batch'] = words(baseline) == words(result['text'])
        assert digest == hashlib.sha256(wav.read_bytes()).hexdigest(), 'Original WAV changed'
        row = {'id':meta['id'], 'sha256':digest, 'duration_seconds':duration,
            'saved_transcript':meta['raw_transcript'], 'batch_text':baseline,
            'batch_compute_ms':batch_ms, 'batch_word_count':len(words(baseline)),
            'attention':args.attention, 'stream_chunk_median_ms':statistics.median(chunk_ms) if chunk_ms else None,
            'stream_chunk_max_ms':max(chunk_ms, default=0), 'variants':variants}
        rows.append(row)
        (args.output/'results.json').write_text(json.dumps(rows,indent=2,ensure_ascii=False))
        print(json.dumps({'completed':index,'total':len(cases),'id':meta['id'],
            'seconds':duration,'batch_ms':round(batch_ms),
            'word_edits':{k:v['word_edits_vs_batch'] for k,v in variants.items()},
            'flush_ms':round(variants['flush_240ms']['flush_compute_ms'])}),flush=True)
    summary = {'recordings':len(rows),'reference':'current batch decoder, not human ground truth',
        'timing':'simulated chunk arrivals; excludes app IPC, WAV saving, insertion, stream teardown',
        'dictionary_terms':terms,'variants':{}}
    for mode in rows[0]['variants']:
        summary['variants'][mode] = {
            'same_words_count':sum(r['variants'][mode]['same_words_as_batch'] for r in rows),
            'word_edits_vs_batch':sum(r['variants'][mode]['word_edits_vs_batch'] for r in rows),
            'reference_words':sum(r['batch_word_count'] for r in rows),
            'median_estimated_after_release_ms':statistics.median(r['variants'][mode]['estimated_after_release_ms'] for r in rows)}
    (args.output/'summary.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary),flush=True)


if __name__ == '__main__':
    main()
