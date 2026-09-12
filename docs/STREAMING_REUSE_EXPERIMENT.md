# Streaming reuse experiment — September 11, 2026

Replayed a frozen set of 35 saved speech recordings, totaling 405.1 seconds, through the pinned local Parakeet model. This includes the dictionary recordings, the five Flow comparison recordings, and longer conversational dictations. Original WAV hashes were checked before and after replay. Audio stayed on this Mac. The installed app's code and models were not rebuilt or replaced.

## Findings

Reusing the existing live transcript is not ready to replace final transcription. Its decoder uses different context and preprocessing from the final batch path, has no dictionary bias, and the app drops the final partial stream chunk at release. Including the remaining audio and padding the ending did not fix the substantial word differences.

A prototype using full-quality batch checkpoints and overlapping final audio came much closer. It keeps the existing dictionary decoder and joins transcripts only where at least eight subword IDs match at consistent audio timestamps. A missing anchor triggers a full-recording fallback. Starting checkpoints at pauses reduced redundant work compared with regular full-prefix updates.

| Prototype | Same normalized word sequence as the existing batch decoder | Word edits relative to batch |
| --- | ---: | ---: |
| Take the last live preview | 4 / 35 | 586 |
| Flush the final audio plus 240 ms silence | 4 / 35 | 595 |
| Transcribe independent chunks at pauses | 25 / 35 | 44 |
| Full-prefix checkpoints every two seconds, overlapping final tail | 31 / 35 | 8 |
| Bound checkpoint work with a rolling window | 29 / 35 | 13 |
| Full-prefix checkpoints at pauses, overlapping final tail | 33 / 35 | 4 |

The reference contains 923 words. These are disagreement counts against the current decoder, **not human-verified word-error rates**. Punctuation and case are ignored; tokenization can count compounds such as “clean up” versus “cleanup” as changes. Parameters were explored on this same set, so these results are development measurements, not a held-out accuracy claim.

The pause/checkpoint prototype actually reused text in 11 longer recordings; nine of those preserved the reference word sequence. The other 24 short recordings still used a full final pass. Its two differing recordings were:

- The final benchmark introduction changed “PhoneOn” to the desired spelling “Phonon.”
- A 54.5-second recording gained “to the” and “if” relative to the current batch output. The audio has not been independently transcribed to adjudicate those additions.

In contrast, the rolling-window prototype introduced clear regressions against the supplied benchmark script, including “text should appear” becoming “texture appears.” The independent pause chunks also lost contextual accuracy. Neither should be enabled in the app.

## Timing and queued work

Simply running full-prefix recognition every two seconds can defeat the speed improvement: a large checkpoint may still be running when recording ends. The final tail has to wait. On the three long benchmark recordings, the final tail computations were about 315, 312, and 573 ms, but estimated completion after release was 554, 1,346, and 1,041 ms after including outstanding work.

The pause/checkpoint strategy had a median final computation of 302 ms and estimated completion of 447 ms among its 11 reuse cases. It still had a 940 ms benchmark case when a checkpoint started shortly before release. These estimates model chunk arrival and sequential work; they exclude native-app scheduling, WAV writing, IPC, paste, and stream teardown. They must not be compared directly with the earlier live Flow latency numbers.

## Testing the existing Streaming-off setting

Inspection of `PillView` confirmed that the installed waveform UI renders microphone levels and recording state, but never displays `previewText`. With Streaming on, the app nevertheless computes partial transcripts while speaking, closes that stream, and then runs the final dictionary-aware batch pass.

The existing Streaming-off setting avoids that unused work and retains the same final recognition path. The waveform uses microphone amplitude directly and does not require streaming ASR. Cleanup remains off, and dictionary recognition remains on.

`scripts/benchmark-finalization.py` compares these two existing paths on the five saved benchmark WAVs at their original pace. It alternates order, measures from the final sample's scheduled arrival, includes outstanding streaming work and stream teardown, and verifies identical final text for each pair. It excludes native recording, WAV saving, IPC, and paste. Detailed measurements are in `target/paced-finalization-2026-09-11/results.json`.

All five paired outputs were exactly identical, including punctuation. Finalization timings were mixed:

| Paced replay | Current streaming + final batch | Streaming off / batch only |
| --- | ---: | ---: |
| Short 1 | 463 ms | 208 ms |
| Short 2 | 217 ms | 200 ms |
| Short median | 340 ms | 204 ms |
| Long 1 | 773 ms | 581 ms |
| Long 2 | 1,196 ms | 1,290 ms |
| Long 3 | 1,250 ms | 1,558 ms |
| Long median | 1,196 ms | 1,290 ms |

Streaming-off was faster on the two short clips but slower on two of three long clips. The test ran on the user's active Mac; system load, GPU power state, and caching were not controlled. These numbers do not establish the cause of that variability. They do not support a consistent overall latency improvement, so the app's existing Streaming setting was left on.

## Reproduction

All runs use the cached model revision `8ae155301e23d820d82aa60d24817c900e69e487`, `parakeet-mlx==0.5.2`, `sentencepiece==0.2.2`, Python 3.12, and dictionary strength 1.5 with the term Phonon. No cleanup model runs.

Launch the scripts with:

```sh
HF_HUB_OFFLINE=1 '/Applications/Phonon Local.app/Contents/Helpers/uv' run \
  --offline --no-project --python 3.12 \
  --with 'parakeet-mlx==0.5.2' --with 'sentencepiece==0.2.2' \
  python -B scripts/benchmark-streaming-reuse.py
```

The initial script snapshots the corpus into ignored results. The other scripts consume that frozen recording list:

- `scripts/benchmark-pause-reuse.py`: independent pause chunks.
- `scripts/benchmark-checkpoint-reuse.py`: overlapping final tail with periodic full-prefix checkpoints.
- Add `--rolling --output target/rolling-reuse-2026-09-11` for bounded checkpoint windows.
- Add `--pause-checkpoints --output target/pause-checkpoint-reuse-2026-09-11` for full-prefix checkpoints at pauses.
- `scripts/benchmark-finalization.py`: paced comparison of the current app's streaming and batch-only modes.

Default detailed outputs live under `target/streaming-reuse-2026-09-11`, `target/pause-reuse-2026-09-11`, `target/checkpoint-reuse-2026-09-11`, and `target/paced-finalization-2026-09-11`. These ignored files contain the private transcripts and timing details. They are not bundled into the app.

Lightweight checks cover anchor overlap, missing anchors, insufficient matches, timestamp mismatches, and script syntax. No production app tests were needed because production code was unchanged.

## Decision

Keep the reuse decoders experimental. Before shipping one, validate transcript changes against audio, use fresh recordings, and handle checkpoint scheduling so large in-flight work cannot erase the latency benefit. The completed paced test did not establish a consistent advantage for Streaming off either. No production code, app settings, permissions, or model files were changed by this experiment.
