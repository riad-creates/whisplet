# Whisplet

**Speak, release, keep going.** Local dictation for Apple Silicon Macs, built on
[Phonon](https://github.com/Infatoshi/phonon). A light native interface, personal
dictionary, optional recording history and a small waveform above the Dock.
No app account or subscription. Your audio is processed on your Mac.

- **Hold to dictate:** F5, Right Option or Fn; Control–Space toggle is also available.
- **Parakeet recognition** via MLX, with decoder confidence work removed and
  unchanged text-state calculations cached in the dictionary-aware decoder.
- **Optional S1-mini cleanup**, off by default. Gemma is not loaded.
- **Local history:** replay, copy and inspect transcripts when saving is enabled.
- **Personal dictionary:** help recognize names and terms, including spoken forms.

## Install

This is a **source-build preview**, for Apple Silicon and macOS 14 or later.
There is no notarized Whisplet download yet. Building on your Mac does not require
paid Apple Developer membership.

Ask your coding agent:

> Clone https://github.com/tobiwsa/whisplet, read AGENTS.md, and help me install it.
> Use F5 hold-to-record with S1 cleanup off.

Or install Apple Command Line Tools, Rust and uv, then:

```bash
git clone https://github.com/tobiwsa/whisplet.git
cd whisplet
bash scripts/install.sh --check
bash scripts/install.sh
```

Open the app path printed by the installer and grant its macOS permissions.
The first launch downloads the local model and runtime. After setup, dictation
works offline. Choose F5 under Settings → Dictation shortcut. On keyboards that
map F5 to system Dictation, use Fn+F5 or enable standard function keys.

[Full installation guide](docs/INSTALL.md) · [Agent instructions](AGENTS.md)

## Update

Quit the app, then run `bash scripts/update.sh` in the same clone. It pulls the
current branch's upstream without overwriting local changes, rebuilds, saves a
backup of the old app and replaces the bundle. It preserves settings, recordings,
the dictionary and downloaded models. No server or background updater is needed.

Local ad hoc signing is free, but macOS may request permissions again after a
rebuild. A saved certificate provides a more stable identity. See the signing
section in the installation guide before changing an existing install.

## How it works

```text
microphone → Parakeet ASR → optional S1-mini cleanup → active text field
```

The interface is SwiftUI/AppKit. A Rust engine manages audio and Python/MLX
sidecars. Models run locally on Apple Silicon. Parakeet uses a final pass over
the recording; streaming currently processes audio during speech but does not
replace that final pass. S1-mini adds English cleanup when enabled, with thinking
disabled. Cleanup time grows with transcript length.

Dictionary recognition biases compatible tokens during decoding; it is not an
unconditional replacement of similar-sounding phrases. Results still need
checking. [Dictionary testing](docs/DICTIONARY_TEST.md).

Recording history is opt-in. The compatibility data store remains
`~/Library/Application Support/Phonon/`; model weights are in the Hugging Face
cache. Do not run this fork alongside Phonon. Screen context is disabled.
No microphone data is uploaded for recognition or cleanup.

## Development

```bash
swift test --disable-sandbox --package-path bar
cargo test --workspace
bash scripts/package-bar.sh
```

| Location | Purpose |
| --- | --- |
| `bar/Sources/` | Native app, shortcuts, history, dictionary, recording pill |
| `crates/` | Rust audio, engine, model lifecycle and CLI |
| `sidecar/` | Local Parakeet and optional S1-mini inference |
| `scripts/` | Install, update, packaging and benchmarks |
| `website/` | Next.js static landing page |

Internal binary and data names retain `phonon` for compatibility. The original
local development install uses `scripts/package-local.sh` to retain its existing
certificate, bundle ID and installation path.

## Credits and license

Whisplet is a modified version of [Phonon by Elliot Arledge / Infatoshi](https://github.com/Infatoshi/phonon),
starting from version 0.1.7. Source remains **GPL-3.0**; keep the original notices
and provide corresponding source when distributing a build. NVIDIA's Parakeet
and Superwhisper's S1-mini retain their respective model licenses. Weights are
not included in this repository. See [LICENSE](LICENSE) and [THIRD_PARTY.md](THIRD_PARTY.md).
