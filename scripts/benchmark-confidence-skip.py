#!/usr/bin/env python3
"""Compare isolated final dictionary ASR optimizations against their baseline.

Uses the frozen local corpus from the streaming experiment, without modifying
audio or app settings. Times final WAV transcription, not microphone-to-paste.
Private transcripts and individual measurements stay in ignored target/.
"""
import argparse
import hashlib
import json
import math
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def signature(result):
    return (result.text, [(t.id, t.text, t.start, t.duration) for t in result.tokens])


def summarize(rows):
    if not rows:
        return {'recordings': 0}
    baseline = [statistics.median(r['baseline_ms']) for r in rows]
    skipped = [statistics.median(r['skip_ms']) for r in rows]
    return {
        'recordings': len(rows),
        'identical_text_and_token_timings': sum(r['identical'] for r in rows),
        'baseline_median_ms': statistics.median(baseline),
        'skip_median_ms': statistics.median(skipped),
        'median_paired_saving_ms': statistics.median(a-b for a, b in zip(baseline, skipped)),
        'median_paired_reduction_percent': statistics.median(
            (a-b)/a*100 for a, b in zip(baseline, skipped)),
        'sum_of_clip_medians_reduction_percent': (1-sum(skipped)/sum(baseline))*100,
        'faster_recordings': sum(b<a for a, b in zip(baseline, skipped)),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path,
                        default=ROOT/'target/streaming-reuse-2026-09-11/manifest.json')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--optimization', choices=['confidence', 'decoder-cache'],
                        default='confidence')
    parser.add_argument('--rounds', type=int, default=4)
    parser.add_argument('--id', action='append', default=[])
    args = parser.parse_args()
    if args.output is None:
        name = 'confidence-skip' if args.optimization == 'confidence' else 'decoder-cache'
        args.output = ROOT/f'target/{name}-2026-09-11'
    if args.rounds < 2 or args.rounds % 2:
        parser.error('--rounds must be an even number of at least 2 for balanced order')
    args.output.mkdir(parents=True, exist_ok=True)

    import mlx.core as mx
    import sentencepiece as spm
    from parakeet_mlx import from_pretrained
    from sidecar.asr_server import transcribe_file
    from sidecar.dictionary_bias import compile_bias, recognition_terms, support_directory

    source = Path.home()/'.cache/huggingface/hub/models--mlx-community--parakeet-tdt-0.6b-v2/snapshots/8ae155301e23d820d82aa60d24817c900e69e487'
    cases = json.loads(args.manifest.read_text())
    if args.id:
        cases = [case for case in cases if case['id'] in args.id]
    if not cases:
        raise SystemExit('No matching recordings')
    for case in cases:
        wav = support_directory()/'Corpus'/case['id']/'audio.wav'
        if hashlib.sha256(wav.read_bytes()).hexdigest() != case['sha256']:
            raise RuntimeError(f"Audio changed since frozen manifest: {case['id']}")
    model = from_pretrained(str(source))
    mx.eval(model.parameters())
    terms = recognition_terms(support_directory())
    tok = spm.SentencePieceProcessor(model_file=str(source/'tokenizer.model'))
    bias = compile_bias(terms, tok, model.vocabulary)
    if bias is None:
        raise SystemExit('Enable dictionary recognition and add a word before benchmarking')
    (args.output/'manifest.json').write_text(json.dumps(cases, indent=2))
    rows = []
    def options(baseline):
        if args.optimization == 'confidence':
            return {'compute_confidence': baseline, 'cache_decoder': False}
        return {'compute_confidence': False, 'cache_decoder': not baseline}

    for index, case in enumerate(cases):
        wav = support_directory()/'Corpus'/case['id']/'audio.wav'
        reference = None
        row = {**case, 'baseline_ms': [], 'skip_ms': [], 'pairs': [], 'identical': True}
        # Warm both modes on this exact shape, outside the timed repetitions.
        for flag in (True, False):
            # Count prediction-network calls only in untimed warmups. Restore
            # the original module before collecting any latency measurements.
            decoder = model.decoder
            calls = 0
            def counted_decoder(*positional, **keywords):
                nonlocal calls
                calls += 1
                return decoder(*positional, **keywords)
            model.decoder = counted_decoder
            try:
                result = transcribe_file(model, str(wav), bias, **options(flag))
            finally:
                model.decoder = decoder
            row['baseline_decoder_calls' if flag else 'skip_decoder_calls'] = calls
            current = signature(result)
            if reference is None:
                reference = current
                row['text'] = result.text
            if current != reference:
                raise AssertionError(f"Warmup output changed: {case['id']}")
            if not all(math.isfinite(t.confidence) if options(flag)['compute_confidence'] else math.isnan(t.confidence)
                       for t in result.tokens):
                raise AssertionError('Unexpected confidence metadata')
        for repeat in range(args.rounds):
            order = (True, False) if (index+repeat) % 2 == 0 else (False, True)
            pair = {'order': ['baseline' if flag else 'skip' for flag in order]}
            for flag in order:
                # The app clears temporary MLX cache when its stream closes.
                # Clear before either mode; loaded model weights stay resident.
                mx.synchronize()
                mx.clear_cache()
                started = time.perf_counter()
                result = transcribe_file(model, str(wav), bias, **options(flag))
                mx.synchronize()
                elapsed = (time.perf_counter()-started)*1000
                mode = 'baseline' if flag else 'skip'
                row[f'{mode}_ms'].append(elapsed)
                pair[f'{mode}_ms'] = elapsed
                if signature(result) != reference:
                    row['identical'] = False
                    (args.output/'mismatch.json').write_text(json.dumps({
                        'id': case['id'], 'mode': mode, 'reference': reference,
                        'actual': signature(result)}, indent=2))
                    raise AssertionError(f"Output changed: {case['id']}")
            row['pairs'].append(pair)
        if hashlib.sha256(wav.read_bytes()).hexdigest() != case['sha256']:
            raise RuntimeError('Original audio changed during replay')
        rows.append(row)
        (args.output/'results.json').write_text(json.dumps(rows, indent=2, ensure_ascii=False))
        print(json.dumps({'completed': len(rows), 'total': len(cases),
                          'seconds': case['duration_seconds'],
                          'baseline_ms': round(statistics.median(row['baseline_ms'])),
                          'skip_ms': round(statistics.median(row['skip_ms'])),
                          'identical': row['identical']}), flush=True)
    summary = {
        'optimization': args.optimization,
        'baseline_options': options(True),
        'optimized_options': options(False),
        'measurement': 'warm model, final WAV ASR only; excludes streaming backlog, capture, IPC and paste',
        'rounds_per_mode_per_recording': args.rounds,
        'dictionary_terms': terms,
        'baseline_decoder_calls': sum(r['baseline_decoder_calls'] for r in rows),
        'optimized_decoder_calls': sum(r['skip_decoder_calls'] for r in rows),
        'all': summarize(rows),
        'short_under_10s': summarize([r for r in rows if r['duration_seconds'] < 10]),
        'long_10s_or_more': summarize([r for r in rows if r['duration_seconds'] >= 10]),
        'peak_mlx_gb': mx.get_peak_memory()/1e9,
    }
    (args.output/'summary.json').write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary), flush=True)


if __name__ == '__main__':
    main()
