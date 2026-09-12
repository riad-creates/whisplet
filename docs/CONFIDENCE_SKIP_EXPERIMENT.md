# Skipping unused ASR confidence scores

September 11, 2026 — Apple M1 Pro, 16 GB unified memory.

The final dictionary-aware transcription now skips token confidence calculation
when called by the app. The model, audio context, dictionary strength, word
selection, duration selection and streaming decoder are unchanged. AI cleanup
remains off; streaming and dictionary recognition remain on.

## Result

All 35 saved recordings (405.1 seconds of audio) produced identical text,
punctuation, token IDs and token timestamps with confidence enabled and disabled.
Four timed repetitions per mode per recording gave 140 paired comparisons.

| Recordings | Count | Median paired time saved | Median paired time reduction |
| --- | ---: | ---: | ---: |
| All | 35 | 10.3 ms | 6.1% |
| Under 10 seconds | 24 | 6.3 ms | 5.2% |
| At least 10 seconds | 11 | 33.2 ms | 8.4% |

Each recording's result is based on its median of four runs. The table then
takes the median of the paired savings/reductions across recordings. The new
path was faster on 34 of 35 recordings; one short clip was about 4 ms slower.
The sum of all recording medians fell by 7.5%.

These are local final-WAV transcription timings, including audio loading,
preprocessing, encoding, decoding and result construction. They exclude
microphone capture, pending streaming work, stream teardown, native app IPC,
WAV saving and text insertion. They do not establish a 6.1% reduction in the
whole shortcut-release-to-paste delay or a new comparison against Wispr Flow.
The Mac was not under controlled laboratory load. Identical output establishes
agreement with the old decoder on these samples, not independently measured
transcription accuracy.

## Implementation

`sidecar/dictionary_bias.py` adds the keyword-only `compute_confidence` argument,
defaulting to true. False skips the softmax, entropy and GPU-to-CPU confidence
read at each decode step. Uncomputed confidence metadata is NaN rather than a
made-up certainty; the app emits only text and elapsed time, so that metadata
does not enter its JSON protocol or history. Existing analysis callers keep
real confidence by default.

`sidecar/asr_server.py` opts out for the app's final transcript. With no active
dictionary bias, the upstream decoder remains unchanged. Live streaming also
retains the upstream implementation. This optimization therefore applies to
the user's current final dictionary recognition path.

## Reproduction and validation

Run `scripts/benchmark-confidence-skip.py` with cached parakeet-mlx 0.5.2,
sentencepiece 0.2.2 and Python 3.12. It defaults to the frozen manifest from the
streaming reuse experiment. The model snapshot is
`mlx-community/parakeet-tdt-0.6b-v2` revision
`8ae155301e23d820d82aa60d24817c900e69e487`, loaded in the runtime's default BF16.

The benchmark warms both modes on each audio shape, alternates their order
across four rounds, clears temporary MLX cache before each timed run (as stream
closure does in the app), and synchronizes the GPU at timing boundaries. It
asserts exact output equivalence and verifies the original WAV hashes before
and after replay. It also checks that confidence is present in the normal path
and marked uncomputed in the skip path. No audio was uploaded.

Private transcripts, individual timings, source snapshots and the summary are
in the ignored `target/confidence-skip-2026-09-11/` directory. Existing ASR and
dictionary tests: 10 passed. Changed Python files passed syntax checks. The
local app was packaged with its persistent certificate; the old and new app
signatures verified with identical designated requirements.

The packaged JSONL sidecar passed a startup transcription, a dictionary-aware
saved recording, strict JSON parsing and clean shutdown. The update was
installed at `/Applications/Phonon Local.app` and relaunched. Microphone,
Accessibility and Input Monitoring still report Granted. The previous signed
app is preserved at
`bar/dist/Phonon Local before confidence skip 2026-09-11.app`.
