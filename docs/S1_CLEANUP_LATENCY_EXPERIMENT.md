# S1 cleanup on the latest dictation test

September 11, 2026 — Apple M1 Pro, 16 GB unified memory.

The user asked to measure S1 on the long passage from their latest live test
and judge whether the edits justify the added wait. Four saved transcripts
from that same test were sent through the installed cleanup sidecar, five
times each. No production code, prompt, model or app setting was changed.

| Audio length | Input words | Output words | Median cleanup | Range |
| --- | ---: | ---: | ---: | ---: |
| 40.6 seconds | 93 | 91 | 647 ms | 637–678 ms |
| 3.1 seconds | 8 | 8 | 182 ms | 179–184 ms |
| 14.6 seconds | 29 | 12 | 213 ms | 208–220 ms |
| 8.4 seconds | 24 | 21 | 248 ms | 247–260 ms |

These timings cover the cleanup JSONL request and response after the app's
normal model warmup. They exclude ASR and native insertion. The same output
was produced on all five runs for each excerpt, with no token-limit fallback.
This process took 2.51 seconds to launch, load and finish its normal warmup;
that startup cost is excluded from the per-request measurements.

## Edit quality

- On the long passage, S1 only removed two words from a verbal stumble. Other
  fillers, repetitions and awkward wording remained. The gain in readability
  was small relative to the additional 0.65 seconds.
- The short sentence gained a comma.
- The S1/latency sentence lost two filler words, gained punctuation, and
  converted the recognized name from words to its intended spelling.
- The 14.6-second passage had a repeated start and a positive aside followed
  by a negative statement about delay. S1 kept the negative statement and
  removed the positive aside as well as the repetition. This is a potentially
  meaningful omission; it should not be treated as wholly successful cleanup.

The long recording's earlier live log measured 956 ms from key release to
insertion with cleanup off. Adding the separately measured cleanup time gives
roughly 1.6 seconds. This is an estimate, not an end-to-end measurement with
cleanup on; scheduling and memory contention could affect a real combined run.
These four excerpts do not establish general cleanup accuracy or latency.

## Reproduction and preservation

`python3 scripts/benchmark-s1-cleanup.py` launches the installed sidecar with
the app's exact prompt and controls: semi-formal styling, prose structure,
general context, thinking disabled and greedy sampling. It uses cached
`mlx-community/S1-mini-MLX-4bit` revision
`5cbd7aec3401144f88a331d385c40b65fd2548eb`, Python 3.12 and mlx-lm 0.31.3.
Both uv and Hugging Face operate offline. The app's sidecar and prompt were
verified to match the workspace versions before the test.

Private input/output text, diagnostics, timing summaries and the readable
before/after comparison are in the ignored
`target/s1-cleanup-latency-2026-09-11/` directory. The benchmark script passed
its syntax check, all 20 requests completed, and the temporary S1 process
shut down cleanly. Original audio and metadata hashes were unchanged, and
the settings hash was unchanged. AI cleanup remains off in Phonon.
