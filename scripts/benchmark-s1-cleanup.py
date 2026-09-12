#!/usr/bin/env python3
"""Time the installed S1 sidecar on saved transcripts without changing the app.

Uses the app's exact prompt, model revision, warmup and JSONL request format.
All model files are resolved offline. Private text/results remain in target/.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import queue
import signal
import statistics
import subprocess
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IDS = [
    'bar_1789170969245_76746',  # 40.6-second passage
    'bar_1789170997388_76746',  # short sentence
    'bar_1789171015930_76746',  # self-correction about the delay
    'bar_1789171051374_76746',  # S1 and latency
]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--id', action='append', default=[])
    parser.add_argument('--rounds', type=int, default=5)
    parser.add_argument('--output', type=Path,
                        default=ROOT/'target/s1-cleanup-latency-2026-09-11')
    args = parser.parse_args()
    if args.rounds < 1:
        parser.error('--rounds must be positive')
    args.output.mkdir(parents=True, exist_ok=True)
    data = Path.home()/'Library/Application Support/Phonon'
    app = Path('/Applications/Phonon Local.app')
    settings_before = digest(data/'settings.json')
    records = []
    for rid in args.id or DEFAULT_IDS:
        directory = data/'Corpus'/rid
        metadata = json.loads((directory/'metadata.json').read_text())
        records.append({
            'id': rid,
            'audio_seconds': metadata['audio_duration_ms']/1000,
            'input_text': metadata['raw_transcript'],
            'audio_sha256': digest(directory/metadata['audio_file']),
            'metadata_sha256': digest(directory/'metadata.json'),
            'audio_file': metadata['audio_file'],
            'runs': [],
        })
    command = [
        str(app/'Contents/Helpers/uv'), 'run', '--offline', '--no-project',
        '--python', '3.12', '--with', 'mlx-lm==0.31.3',
        'python', '-B', str(app/'Contents/Resources/sidecar/polish_server.py'),
        '--model', 'mlx-community/S1-mini-MLX-4bit',
        '--revision', '5cbd7aec3401144f88a331d385c40b65fd2548eb',
        '--system-prompt-file', str(app/'Contents/Resources/prompts/s1_mini.txt'),
    ]
    events = queue.Queue()
    process = None
    with (args.output/'stderr.log').open('w') as stderr:
        try:
            started = time.perf_counter()
            process = subprocess.Popen(
                command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=stderr, text=True, bufsize=1, start_new_session=True,
                env={**os.environ, 'HF_HUB_OFFLINE': '1', 'HF_HUB_DISABLE_TELEMETRY': '1'})

            def read_output():
                for line in process.stdout:
                    events.put(line)
                events.put(None)

            threading.Thread(target=read_output, daemon=True).start()

            def request(payload):
                process.stdin.write(json.dumps(payload)+'\n')
                process.stdin.flush()
                while True:
                    line = events.get(timeout=120)
                    if line is None:
                        raise RuntimeError('S1 sidecar exited before replying; see stderr.log')
                    response = json.loads(line)
                    if response.get('ok') is False:
                        raise RuntimeError(response)
                    if response.get('status', {}).get('state') == 'loading':
                        continue
                    return response

            warmup = request({'command': 'warmup'})
            ready_ms = (time.perf_counter()-started)*1000
            assert warmup.get('status', {}).get('state') == 'ready', warmup
            print(json.dumps({'ready_ms': round(ready_ms), 'cases': len(records),
                              'rounds': args.rounds}), flush=True)
            for repeat in range(args.rounds):
                order = records[repeat % len(records):] + records[:repeat % len(records)]
                for record in order:
                    started = time.perf_counter()
                    response = request({'command': 'run', 'inputText': record['input_text']})
                    wall_ms = (time.perf_counter()-started)*1000
                    if 'outputText' not in response:
                        raise RuntimeError(response)
                    record['runs'].append({
                        'round': repeat+1, 'request_wall_ms': wall_ms,
                        'output_text': response['outputText'],
                        'diagnostics': response['diagnostics'],
                    })
                    (args.output/'results.json').write_text(
                        json.dumps(records, indent=2, ensure_ascii=False))
                    print(json.dumps({'id': record['id'], 'round': repeat+1,
                                      'request_ms': round(wall_ms),
                                      'output_words': len(response['outputText'].split()),
                                      'fallbacks': response['diagnostics']['fallbackChunkCount']}), flush=True)
            process.stdin.write(json.dumps({'command': 'shutdown'})+'\n')
            process.stdin.flush()
            process.wait(timeout=15)
            if process.returncode:
                raise RuntimeError(f'Sidecar exited with {process.returncode}')
        finally:
            if process is not None and process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()

    assert digest(data/'settings.json') == settings_before, 'App settings changed during test'
    for record in records:
        directory = data/'Corpus'/record['id']
        assert digest(directory/record['audio_file']) == record['audio_sha256']
        assert digest(directory/'metadata.json') == record['metadata_sha256']
    summary = {
        'measurement': 'S1 cleanup request only, after normal app warmup; excludes ASR and native insertion',
        'model': 'mlx-community/S1-mini-MLX-4bit',
        'revision': '5cbd7aec3401144f88a331d385c40b65fd2548eb',
        'runtime': 'mlx-lm==0.31.3',
        'control': '[Styling: semi-formal] [Structure: prose] [Context: general]',
        'process_start_to_ready_ms': ready_ms,
        'rounds': args.rounds,
        'settings_unchanged': True,
        'original_recordings_unchanged': True,
        'cases': [],
    }
    for record in records:
        runs = record['runs']
        times = [r['request_wall_ms'] for r in runs]
        summary['cases'].append({
            'id': record['id'], 'audio_seconds': record['audio_seconds'],
            'input_words': len(record['input_text'].split()),
            'median_request_ms': statistics.median(times),
            'min_request_ms': min(times), 'max_request_ms': max(times),
            'median_first_token_ms': statistics.median(
                r['diagnostics']['timeToFirstTokenMilliseconds'] for r in runs),
            'distinct_outputs': len({r['output_text'] for r in runs}),
            'fallback_chunks': sum(r['diagnostics']['fallbackChunkCount'] for r in runs),
        })
    (args.output/'summary.json').write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary), flush=True)


if __name__ == '__main__':
    main()
