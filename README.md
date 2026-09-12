# Phonon

Local customization of Phonon 0.1.7: Parakeet dictation with optional **S1-mini by Superwhisper** cleanup.

Use **Phonon Local → Settings → AI cleanup**. On cleans English transcripts; off uses Parakeet alone and unloads the cleanup process. The choice is saved and changes wait for the current dictation to finish. This build shares your Phonon settings, history, and dictionary; run only one copy at a time.

S1-mini uses the model's exact trained prompt, with thinking disabled. Long transcripts are split at sentence or word boundaries into at most 768 transcript tokens per model request. If a request hits its output cap or returns blank, that section keeps its original transcript. A single oversized unbroken word also passes through unchanged. Cleanup time still grows with transcript length; this does not change Parakeet's audio handling.

This model supports English cleanup and does not accept Phonon's screen-context or fuzzy dictionary prompts. Screen context is disabled in this build. Explicit dictionary replacements still run when cleanup is on.

**Dictionary recognition** in Settings is an independent, experimental ASR option. Spelling terms (entries without a replacement) are tokenized with Parakeet's own tokenizer and receive bounded bonuses during final greedy TDT decoding. Blank predictions and duration scores are unchanged. Live preview remains stock Parakeet. Changes to Dictionary or the switch apply to the next final pass without restarting. This works with AI cleanup either on or off; recognized terms regain their dictionary capitalization, without replacing sound-alike phrases such as “phone on.” See [the test guide](docs/DICTIONARY_TEST.md).

Build the separate local app (requires Rust, Swift, uv, and a persistent signing certificate):

```bash
bash scripts/package-local.sh
```

The result is `bar/dist/Phonon Local.app`. The local wrapper uses the certificate fingerprint saved in the git-ignored `.phonon-local-signing-identity`, or an explicit `PHONON_CODESIGN_IDENTITY`. It refuses ad hoc signing. Use the same certificate and bundle ID across updates so macOS can recognize the app; changing from the old ad hoc builds may require one final permission setup. This is an Apple Development-signed local build, separate from the notarized upstream release. See [local signing and permission recovery](docs/LOCAL_BUILD.md#signing-and-permissions).

[Website](https://phonon.sh) · [Distribution plan](DISTRIBUTION.md)

## Upstream installation (without these changes)

```bash
brew install --cask infatoshi/phonon/phonon
phonon
```

The cask installs the Developer ID-signed and notarized app. On first launch
Phonon downloads the open Parakeet and Gemma weights, both pinned to exact
revisions, which is about 5.6 GB and the one slow start. Everything after that
is local and offline. Tagged releases also include the DMG for direct
installation. To build locally instead, use
`brew install --formula infatoshi/phonon/phonon`.

## Pipeline

```
mic → Parakeet ASR → optional S1-mini by Superwhisper cleanup → clipboard / type
```

Parakeet warms batch and streaming ASR. When AI cleanup is on, the loader also waits for the correction model and a transcript-cleanup smoke test. When off, only Parakeet is needed. The engine command `{"cmd":"set_cleanup","enabled":false}` changes the live mode; `PHONON_AI_CLEANUP=0` overrides startup for command-line use.

The correction stage is `sidecar/polish_server.py`: S1-mini by Superwhisper, converted to MLX 4-bit by `mlx-community/S1-mini-MLX-4bit`, pinned to revision `5cbd7aec3401144f88a331d385c40b65fd2548eb`. It runs locally via `mlx-lm==0.31.3` and `uv`. Gemma is not loaded by this build.

## Build from source

```bash
cargo install --path crates/phonon-cli --force --root ~/.local
phonon bar --rebuild   # once, builds Swift floating pill
```

## Commands

```bash
phonon                 # native macOS app
phonon bar             # explicit native-app launcher
phonon engine          # warm JSONL backend (bar uses this)
phonon doctor
phonon bench
phonon profile --help   # discover kernel, model, and end-to-end profilers
phonon profile kernel   # literal MLX Metal kernel top 10 for a warmed request
phonon profile model    # warm-only LLM prefill / decode sweep
phonon profile e2e      # summarize real keyboard-to-insertion traces
phonon dictionary --help # terms, replacements, Wispr import, correction evaluation
phonon dictionary import-txt # activate dictionary_new_terms.txt
phonon corpus --help     # paired WAV/metadata corpus + intended transcripts
phonon stats             # local words, sessions, speaking time, dictionary fixes
```

## Surviving an uninstall

Uninstallers match on the app name, the developer name, or the bundle
identifier, then delete every hit under `~/Library/Application Support`,
`Preferences`, `Caches`, `Logs`, and `Saved Application State`. Nothing kept
there can survive one.

So Phonon mirrors the small irreplaceable files to `~/.phonon/backup`, which no
such pattern reaches: the dictionary, settings, history, vocabulary and word
replacements, about 128 KB. The mirror is rewritten whenever any of them change,
and a wiped store can never overwrite a populated backup.

If Phonon ever starts with an empty data folder while that backup exists, it
asks whether to restore it, and offers to delete it instead. It never restores
silently. Settings › Backup shows what is held, reveals it in Finder, deletes
it, and exports everything including the corpus.

Model weights are unaffected. They live in `~/.cache/huggingface`, are named
after the models rather than the app, and no uninstaller touches them.

## Known issues

- Opening Phonon can pull a connected Bluetooth headset into the hands-free
  profile, which degrades its output quality. Reselect the input in System
  Settings › Sound as a workaround.
  See [#9](https://github.com/Infatoshi/phonon/issues/9).

## Local data and correction loop

Nothing is retained until you say so. On first launch the app asks once whether
to keep local history and whether to use active-window context; both start off,
and declining leaves dictation fully working. Settings carries the retention
window (keep until deleted, or 7 / 30 / 90 days) and a clear-everything button.

With local history on, every native-app recording is retained as a paired corpus
item:

```text
~/Library/Application Support/Phonon/
├── dictionary.json
├── settings.json
└── Corpus/
    └── <source>_<timestamp>_<process>/
        ├── audio.wav
        └── metadata.json
```

`metadata.json` keeps the raw ASR transcript, final correction, optional intended
transcript, dictionary changes, source, duration, and LLM timings. Useful loops:

Before ASR, an adaptive audio gate requires sustained speech-like energy above
the clip's measured noise floor. Clips without speech remain in the corpus with
`speech_detected: false`, skip Parakeet and the correction model entirely, and produce no text.

```bash
phonon dictionary import-wispr
phonon dictionary import-txt
phonon dictionary test 'run v llm on black well'
phonon dictionary evaluate
phonon corpus list --search Blackwell
phonon corpus show <id>
phonon corpus set-intended <id> 'intended ground truth'
phonon dictionary learn <id> --from 'black well' --to Blackwell
```

When `screen_context` is enabled in `settings.json`, the floating bar captures
each visible display once at recording start and runs local macOS Vision OCR.
Screenshots are discarded immediately. The engine uses OCR only to rank
dictionary candidates already relevant to the spoken transcript; it sends
confirmed terms, not the full screen text, into the correction prompt.

### Floating bar

- One bottom-anchored capsule that expands itself; no spawned overlay or inner waveform
- Warm voice-responsive fill while listening; the same capsule breathes while processing
- **hold Right Option (⌥)** PTT → release → ASR → auto-polish → types into frontmost app
- Ctrl+Space toggle; multi-pass OK

Settings picks which of those is live. Right Option and Globe (fn) are both
offered as the hold key, each on its own or paired with the Ctrl+Space toggle.
macOS also acts on the Globe key, so set System Settings › Keyboard ›
"Press 🌐 key to" to "Do Nothing" before choosing it.

Recording cues are off by default. Turning them on plays a short rising sweep
when a recording opens and a falling one when it closes. Both are synthesized by
`scripts/make-cue-sounds.py`; no audio is sampled or downloaded.

Needs: Mic + Accessibility + Input Monitoring.

### Native app

`phonon` launches a regular macOS Dock app with a dark ember theme. Its native
Home, History, Dictionary, and Settings surfaces read and write the same JSON
and paired corpus used by the engine and CLI. Model status exposes parallel
weight loading, startup smoke tests, TTFT, and decode throughput. The
menubar `ϕ` remains available as a compact shortcut while the app is running.

The native app uses a configurable microphone priority list. Availability is
refreshed before each recording, so a preferred external microphone can take
over automatically when connected. The bar menu shows the microphone selected
by Auto.

## Layout

```
crates/phonon-audio/   recording and audio file ownership
crates/phonon-asr/     Parakeet sidecar lifecycle + protocol
crates/phonon-llm/     correction sidecar lifecycle + benchmark client
crates/phonon-profile/ literal Metal dispatch, LLM phase, and E2E profilers
crates/phonon-core/    pipeline coordination + engine events
crates/phonon-cli/     commands, doctor, bench, bar launcher
bar/                   SwiftPM native Home/History/Dictionary/Settings app + floating pill
sidecar/asr_server.py
sidecar/polish_server.py
assets/english_words.txt
prompts/s1_mini.txt
```

## License

Phonon source is GPL-3.0. Downloaded model weights retain their upstream
licenses and are not stored in this repository. See [THIRD_PARTY.md](THIRD_PARTY.md).
