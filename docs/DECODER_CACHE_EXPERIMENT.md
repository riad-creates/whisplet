# Reusing unchanged prediction-network results

September 11, 2026 — Apple M1 Pro, 16 GB unified memory.

The final dictionary-aware decoder can now reuse its prediction-network output
and prospective next hidden state after a blank. A blank advances through
audio without committing a new text token or hidden state, so the prediction
network's inputs have not changed. Every emitted token invalidates the cache,
including repeated token IDs. The cache is local to each utterance and cannot
carry over to another batch item or recording.

The audio encoder and joint network still run as before. No model weights,
audio context, dictionary strength, duration decisions or streaming behavior
were changed. The previously installed confidence-skipping optimization remains
enabled. This experiment compares against that version, not the earlier version
that computed confidence.

## Result

35 frozen recordings, totaling 405.1 seconds of audio, produced identical text,
punctuation, token IDs and token timestamps. Four timed repetitions per mode
per recording gave 140 paired comparisons.

| Recordings | Count | Median paired time saved | Median paired time reduction |
| --- | ---: | ---: | ---: |
| All | 35 | 3.2 ms | 2.2% |
| Under 10 seconds | 24 | 2.0 ms | 1.7% |
| At least 10 seconds | 11 | 12.2 ms | 3.0% |

Each recording contributes the median of four timings per mode; the table then
takes the median of its paired savings/reduction. The optimized path was faster
on 31 of 35 recordings. The sum of all recording medians fell by 3.0%.

Untimed instrumentation counted 2,149 prediction-network calls without caching
versus 1,733 with caching over one replay of the corpus: 416 calls avoided, or
19.4%. The counter was removed before collecting latency measurements. This
call reduction concerns the prediction network, not all neural-network work.

These are warm-model, final-WAV transcription measurements. They exclude
microphone capture, pending streaming work, stream teardown, native IPC, WAV
saving and text insertion. They do not establish an equivalent improvement in
release-to-paste latency. The Mac was not under controlled laboratory load;
the measured gains are small. Agreement with the previous decoder on this
sample is not independent ground-truth transcription accuracy.

## Implementation and validation

`generate_with_bias` and `transcribe_file` accept `cache_decoder`, default false
for compatibility and comparison. The app's JSONL transcription path enables
it, alongside `compute_confidence=False`. The upstream no-dictionary and
streaming paths are unchanged.

Run `scripts/benchmark-confidence-skip.py --optimization decoder-cache` using
the cached Python 3.12 runtime with parakeet-mlx 0.5.2 and sentencepiece 0.2.2.
Both modes disable confidence; only caching differs. The benchmark warms both
modes on each shape, alternates order across four rounds, clears temporary MLX
cache before each timing, and synchronizes the GPU at timing boundaries.
The existing model remains `mlx-community/parakeet-tdt-0.6b-v2` revision
`8ae155301e23d820d82aa60d24817c900e69e487`, using the runtime's default BF16.

Original WAV hashes were verified before and after replay. Private transcripts,
individual timings, call counts and baseline source snapshots are retained in
the ignored `target/decoder-cache-2026-09-11/` directory. No audio was uploaded.

Twelve ASR/dictionary tests passed, including deterministic regression cases
for initial blanks, repeated token IDs, zero-duration steps with forced frame
advancement, separate batch items, and consecutive transcription calls. Changed
Python files passed syntax checks.

The signed app was packaged successfully. Its ASR sidecar passed a startup
transcription, a saved dictionary recording, strict JSON parsing and clean
shutdown. The old and new signatures verified with identical designated
requirements. The update was installed at `/Applications/Phonon Local.app` and
relaunched; Microphone, Accessibility and Input Monitoring remained Granted.
Settings, dictionary and all 35 original recordings were verified unchanged.
The preceding signed app is retained at
`bar/dist/Phonon Local before decoder cache 2026-09-11.app`.
