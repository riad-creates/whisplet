# Testing dictionary recognition

“Phonon” is saved as a spelling term, with no replacement and no “phone on” alias. Settings → Dictionary recognition enables the experimental final-transcript decoder. It defaults to on. The saved setting is `dictionary_recognition`; Dictionary and setting edits are read before each final batch transcription. Live preview is unchanged.

## Try with your voice

The local rebuild can require renewed macOS permissions. If Home reports **Microphone Not requested** or **Accessibility Needs access**, grant those using Home's permission controls before testing. Input Monitoring must also show Granted. Screen Recording is unnecessary for this experiment. Settings remain usable before microphone approval.

1. Open an empty text field in an app where dictation already works.
2. In Phonon Local Settings, turn **AI cleanup off** for both rounds so S1-mini by Superwhisper cannot change the comparison.
3. Turn **Dictionary recognition off**. Dictate each sentence separately, using your normal pronunciation. Note the final pasted text.
4. Turn **Dictionary recognition on** and repeat the same sentences a few times. Wait for the final pasted text; the live preview may still show “phone on.”
5. Turn AI cleanup back on afterward if desired.

Name examples:

- I use Phonon for dictation.
- Phonon is running on my Mac.
- Please open Phonon.

Ordinary speech controls:

- Put my phone on the table.
- Please turn the phone on.
- I left my phone on the charger.

Report both remaining misses and unwanted conversions. This is a preference, not a guarantee. Increasing the boost can damage ordinary speech, so the initial strength is deliberately modest.

## Implementation and validation

Parakeet TDT v2, MLX revision `8ae155301e23d820d82aa60d24817c900e69e487`, runtime `parakeet-mlx==0.5.2`, tokenizer runtime `sentencepiece==0.2.2`.

Dictionary spellings and lowercase variants map to existing token IDs. A prefix graph gives a 0.375-logit bonus at phrase starts and a maximum 1.5-logit continuation bonus. Bonuses do not accumulate across duplicate entries. A winning blank remains blank; duration predictions and model weights are unchanged. No user audio examples are enrolled. Case restoration only matches the already-recognized word, never “phone on” as a substitute for “Phonon.”

On September 10, 2026, synthetic speech generated locally with macOS Samantha showed:

- “I use Phonon for dictation”: baseline “phone on,” boosted “phonon.”
- “Phonon is running on my Mac”: baseline “Phone on,” boosted “Phonon.”
- “Please open Phonon” and “I installed phone on yesterday” still produced “phone on.”
- One further app-name example was already correct in the baseline.
- Six ordinary-speech controls were unchanged, including all three “phone on” sentences above.

These are synthetic fixture results, not an accuracy estimate for your voice. The packaged engine separately passed on/off/empty-dictionary/live-edit tests using the same audio, including canonical case restoration and an ordinary-speech control. Rust workspace tests (34), Swift tests (41), and Python tests (16) passed; the final app bundle compiled and its signature was verified.

The local synthetic experiment is reproducible with `scripts/test-dictionary-recognition.py`. It uses the cached model, macOS `say`/`afconvert`, and the two pinned Python runtime requirements above, and writes fixtures/results under `target/dictionary-recognition-test/`.
