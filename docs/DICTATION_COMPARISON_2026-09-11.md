# Phonon Local and Wispr Flow: spoken comparison

Measured on September 11, 2026, from the user's alternating readings of the supplied short sentence and longer passage. Five matching recordings were found per app: two short and three long. Only those recordings were included. No application settings or code were changed for this analysis.

## Delay after recording stops

Values are milliseconds. Phonon logs keyboard release to completion of the text insertion call; Flow's installed code stores `e2eLatency` from the recorder's absolute stop time through its completion path. These are useful practical measurements, but they do not have identical boundaries and are not an independent measurement of the text becoming visible on screen.

| Passage | Trials per app | Phonon median | Flow median | Phonon range | Flow range |
| --- | ---: | ---: | ---: | ---: | ---: |
| Short, about 4–5 seconds | 2 | 698 | 308 | 613–782 | 291–325 |
| Long, about 26–30 seconds | 3 | 1,111 | 1,214 | 897–1,127 | 964–1,214 |

Flow's short median was 390 ms lower. Phonon's long median was 103 ms lower, with overlapping ranges and too few trials to establish a reliable long-passage winner.

## Individual attempts

Phonon timestamps are completion times. Flow timestamps are saved recording timestamps, so timestamps should not be interpreted as the same event across apps. All times below are UTC.

| Passage / attempt | Phonon pass | Phonon timestamp | Phonon recording seconds | Phonon delay ms | Flow timestamp | Flow recording seconds | Flow delay ms |
| --- | --- | --- | ---: | ---: | --- | ---: | ---: |
| Short 1 | p15 | 20:38:25 | 5.19 | 782 | 20:38:29.744 | 4.16 | 325 |
| Short 2 | p16 | 20:38:56 | 5.08 | 613 | 20:38:57.392 | 4.88 | 291 |
| Long 1 | p17 | 20:39:33 | 26.70 | 897 | 20:39:44.498 | 26.48 | 1,214 |
| Long 2 | p18 | 20:40:56 | 28.17 | 1,111 | 20:41:01.470 | 27.80 | 964 |
| Long 3 | p19 | 20:42:05 | 28.59 | 1,127 | 20:42:11.867 | 29.56 | 1,214 |

The third long attempt included a spoken introduction identifying each app.

## Text output

- Both apps preserved the short sentence's words. Flow included an Oxford comma; Phonon omitted it.
- Flow's raw long transcripts contained the spoken sequence markers and the Tuesday-to-Wednesday correction. Its formatted output converted the three items into a numbered list and retained Wednesday alone in all three attempts.
- The saved Flow formatting uses an HTML ordered list; the saved pasted text has numbered lines. This directly demonstrates a formatting stage after recognition.
- On two long attempts, Flow's raw transcript said “punctuations”; the formatting stage changed it to “punctuation.” On the final attempt it also removed the repeated phrase “the next the next.”
- Phonon's raw and final transcripts matched, consistent with cleanup being disabled. It retained the self-correction and prose structure. Relative to the supplied script, all three long outputs said “list” instead of “lists,” and the first said “shortcuts” instead of “shortcut.” Its final introduction spelled the app name “PhoneOn.”
- Flow's final attempt retained “result” rather than the script's “results.”

These are text comparisons, not audio-verified recognition errors. Each app received a separate live reading, and the recorded audio was not replayed to determine exactly what was spoken.

## Where Phonon spent time

On the two short attempts, Phonon's transcription request stage took 752 and 580 ms; the final ASR worker reported 201 and 442 ms respectively. The remainder includes work and waiting outside that reported final pass. The current app also performs streaming recognition before a final full-recording pass. Profiling the handoff, outstanding streaming work, and final-pass duplication is a better-supported next investigation than assuming model inference accounts for the whole delay.

Actual insertion took about 1 ms, WAV preparation about 7–11 ms, and the cleanup-disabled handoff about 19 ms on the short attempts. No cleanup model inference ran.

## Limits and sources

- Small sample: two short and three long attempts per app; no independently identified warm-up trial was excluded from these matching readings.
- Flow formatting was enabled (`formatted` status and changed long output); Phonon cleanup was disabled (zero reported LLM inference and matching raw/final output).
- Flow's history labels the input “Built-in mic (recommended).” Phonon is configured to prefer WH-1000XM6, then the built-in mic, but does not save the actual selected device in these recording metadata. Matching microphones during this run is therefore unverified.
- Separate readings differ slightly in pace and wording. Network and system load were not controlled.
- A screen recording is not needed for these log comparisons, but would be needed for an independent visual-delay check.
- Source: `~/Library/Logs/Phonon/e2e.jsonl`, matched with the five corresponding `~/Library/Application Support/Phonon/Corpus/bar_*/metadata.json` files.
- Source: read-only live SQLite query of `~/Library/Application Support/Wispr Flow/flow.sqlite`, including its WAL, restricted to the test time window and script text. Flow record IDs: `fb896b16-f817-4785-830d-e7caed74fbec`, `dc3dfec9-0ae8-4aa9-a660-702020f18ac0`, `e57665bc-811b-4e0f-9488-baf1c3b44579`, `fd02f592-e36e-4645-a0e8-38bbfcb245e3`, `5d4ad25c-f5a7-4625-b4cb-b81fb170d7ab`.
