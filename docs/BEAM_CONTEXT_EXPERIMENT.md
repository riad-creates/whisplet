# Dictionary beam search and S1 context experiment

Tested locally on 2026-09-11. **Prototype only; the installed app was not rebuilt or changed.**

The prototype recognizes Phonon in all seven name-containing user recordings, versus four with the installed dictionary decoder. It also preserves the ordinary “phone on the table” recording. However, a final set of new synthetic phrases exposes false replacements and a clipped sentence ending. This version is not ready to become the default dictation path.

## What was tested

Eight specific saved user recordings were replayed, together with 50 synthetic recordings. The eight original WAV hashes still match the earlier replay. No unrelated dictations were processed, and no recordings were sent to a service.

The experiment uses the already cached Parakeet TDT 600M v2 and S1-mini 4-bit models. S1 scores possible transcripts; it does not generate rewritten sentences or receive audio. Its conditioning prompt is the existing S1 normalization prompt plus a first-pass transcript.

The most successful prototype:

1. Encodes the audio with Parakeet.
2. Runs a beam search with a reward for complete dictionary words, refunding abandoned partial-word preferences.
3. Runs a separate search with no dictionary reward, so dictionary preference cannot eliminate every ordinary-word alternative.
4. Keeps the four highest-ranking candidates plus the separate search's best result.
5. Uses S1 to score that short list and combines the scores with the speech and dictionary scores.

The fixed validation parameters were beam width 6, dictionary reward 4, and context weight 0.1. Search scores are approximate ranking scores, not calibrated probabilities. In particular, alignment sums depend on the search paths retained.

## The user's recordings

Canonical dictionary capitalization is applied to the outputs below. These are recognition comparisons, not independently verified reference transcripts.

| Recording | Installed decoder | Prototype |
| --- | --- | --- |
| 1 | Phonon runs on my Mac. | Phonon runs on my Mac. |
| 2 | Hey, Phonon, can you help with this? | Hey, Phonon, can you help with this? |
| 3 | Pull my phone on the table. | Pull my phone on the table. |
| 4 | Phonon helps with dictation. | Phonon helps with dictation. |
| 5 | Interesting. It seems Phonon is working now. | Interesting. It seems Phonon is working now. |
| 6 | Phone on, phone on. | Phonon, Phonon. |
| 7 | The Phon app is working really well. | The Phonon app is working really well. |
| 8 | Why is the phone on app working well now? | Why is the Phonon app working well now? |

For recording 3, beam search alone chose “Put,” while context scoring restored “Pull.” The intended first word has not been independently verified; this is not counted as an accuracy improvement or regression.

## Regression checks

The stronger dictionary beam alone changed “phoning,” “phony,” “photon,” and “phone only” into Phonon in the first 24 new synthetic tests. S1 fixed three of these when the correct candidate was present. Preserving the separate search's best result allowed it to fix “Phone only” as well.

After that adjustment, the prototype preserved all 27 ordinary-speech controls in the development set and recognized Phonon in its three synthetic name examples. Those results informed the prototype, so they are not an independent final evaluation.

With the parameters frozen, 20 additional phrases were synthesized at alternating speaking rates:

- All six name-containing phrases included Phonon in the output, but one lost the sentence ending: “Is Phonon still listening?” became “Is Phonon still listen”.
- Twelve of fourteen ordinary-speech phrases preserved their words.
- “This is a phony invoice” became “This is a Phonon voice”.
- “A photon has no rest mass” became “A Phonon has no rest mass”.

Increasing context weight to 0.25 after seeing these results fixes the two false replacements on those same candidates, but leaves the clipped ending. That is retrospective tuning, not a new validation pass. Still larger context weights also restore unwanted “phone on” spellings in earlier name tests.

These synthetic tests use macOS Samantha. They are useful for finding regressions but do not establish performance on the user's voice, noise, long dictations, accents, or other dictionary terms.

## Measured cost on this Mac

For the final 20 short synthetic clips, excluding the first clip:

| Stage | Median |
| --- | ---: |
| First-pass transcript for S1's prompt | 114 ms |
| Audio encoding for beam search | 57 ms |
| Two beam searches | 181 ms |
| S1 candidate scoring | 245 ms |
| Beam and context pipeline, excluding first pass | 498 ms |
| Complete prototype, including first pass | 620 ms |

Complete prototype times ranged from 516 to 1,723 ms. The implementation re-encodes audio for the beam pass; sharing that work is a possible optimization. These are local processing times, not microphone-to-paste measurements, and exclude model startup. Long recordings were not benchmarked.

S1 scoring alone on the earlier short-list replay had a median of 178 ms, compared with roughly one second when scoring the much larger candidate lists.

Peak MLX allocation with both models in the validation process was **2.42 GB**. This is not total app RAM: Python, the native app, caches, and other process overhead are not included. Model loading in that run took approximately 7.7 seconds for Parakeet and 0.8 seconds for S1 from local caches.

## Decision

Keep the current installed decoder for now. The experiment demonstrates a useful accuracy improvement on the user's examples, but it also demonstrates regressions on unfamiliar phrases. Before integrating it, the decoder needs better handling of sentence endings and more reliable comparison of dictionary candidates against the original audio. Any future S1 recognition mode should have its own visible setting, since AI cleanup is currently disabled.

The next evaluation should retain this complete regression set and add fresh user recordings. Increasing a score until existing examples pass is not sufficient evidence to ship it.

## Reproduction and artifacts

All experiment code and detailed outputs are in `target/beam-context-2026-09-11/` (an ignored local directory):

- `baseline.py`, `baseline.json`: upstream beam search without dictionary changes.
- `phrase_beam.py`: experimental dictionary-aware decoder.
- `run_phrase_beam.py`, `phrase-beam.json`: saved recordings and initial controls.
- `check_fresh_controls.py`, `fresh-controls.json`: first 24 synthetic probes.
- `mixed_candidates.py`, `mixed-candidates.json`: preserve a separate unbiased candidate search.
- `rank_context.py`, `mixed-shortlist-context-ranking.json`: S1 scoring and weight comparisons.
- `validate_mixed.py`, `validation-results.json`: final fixed-parameter validation and timings.

The scripts use the pinned local snapshots already used by the app. The final validation can be rerun from the repository root with:

```sh
HF_HUB_OFFLINE=1 '/Applications/Phonon Local.app/Contents/Helpers/uv' run \
  --offline --no-project --python 3.12 \
  --with 'parakeet-mlx==0.5.2' --with 'sentencepiece==0.2.2' \
  --with 'mlx-lm==0.31.3' \
  python -B target/beam-context-2026-09-11/validate_mixed.py
```

Running this regenerates the validation report but does not install anything. Existing synthetic WAV files are reused. The initial user-recording replays additionally depend on the fixture manifest in `target/dictionary-replay-2026-09-11/results.json`.
