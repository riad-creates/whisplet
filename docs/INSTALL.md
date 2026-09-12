# Install Whisplet from GitHub

This is a **source-build preview** for Apple Silicon Macs (M1 or later), macOS 14
or later. Your Mac compiles the app. You do not need an app login or paid Apple
Developer membership. Initial setup needs internet access for tools and models;
dictation runs locally once those downloads finish. Allow several GB of free
disk space for models, runtime dependencies and build files.

## Let an agent install it

Give your coding agent this request:

> Clone https://github.com/riad-creates/whisplet, read its AGENTS.md, and help me build
> and install Whisplet on this Mac. Use F5 hold-to-record and keep S1 cleanup off.
> Preserve existing recordings, settings and signing identity if updating.

Your agent can install/build software. You still approve macOS privacy prompts.
Only run installation code from a repository you trust.

## Install yourself

Requirements:

- Apple Command Line Tools: `xcode-select --install` (complete the macOS dialog).
- [Rust](https://rustup.rs): install the stable toolchain, then reopen Terminal.
- [uv](https://docs.astral.sh/uv/getting-started/installation/): `brew install uv`
  if you already use Homebrew. Python dependencies are managed by uv.

```bash
git clone https://github.com/riad-creates/whisplet.git
cd whisplet
bash scripts/install.sh --check
bash scripts/install.sh
open "$HOME/Applications/Whisplet.app"
```

The last path is the default for a fresh install. Use the exact path printed by
the installer for an existing local development installation instead.
To use a different install directory, set `WHISPLET_INSTALL_DIR` to an absolute
path on every install/update. Keep it stable; the default requires no sudo.

On first launch:

1. Allow Microphone, Accessibility and Input Monitoring as prompted. Screen
   Recording is unnecessary for this build.
2. Wait until the model loader finishes. Parakeet downloads once; S1 is only
   needed if you turn on AI cleanup. Existing model caches are reused.
3. Choose your microphone and shortcut in Settings. For F5, select **F5 hold**.
   Hold, speak, and release in a text field. If macOS handles the physical key
   as Dictation, use Fn+F5 or enable standard function keys in Keyboard settings.
4. Choose whether to save local recording history. Cleanup is off by default;
   history can also remain off without affecting dictation.

## Updates and rollback

Quit the app after finishing any recording, then in the same clone:

```bash
bash scripts/update.sh
```

This fetches the current branch's upstream with a fast-forward-only pull and
rebuilds the app. It stops if the checkout has uncommitted changes. It does not
silently replace files you edited. Launch the installed app again afterward.

Each replacement backs up the previous app under `target/install-backups/` in
your clone. To roll back, quit the app, extract that backup, and restore it to
the same installation path. Do not delete the application-support directory.
Settings, dictionary, recordings, backups and model caches are untouched by
installation and updating. There is no automatic update service yet.

## Signing: free local builds versus downloadable releases

The installer uses an existing Apple Development/Developer ID identity when
available and remembers it in a git-ignored file. Otherwise, it creates an
**ad hoc signature**, which requires no certificate or paid account. Ad hoc
builds may need Accessibility/Input Monitoring permissions again after updates.
That is a macOS identity limitation, not something AGENTS.md can remove.

A downloaded prebuilt app has the same macOS security checks whether hosted on
GitHub or another website. Developer ID signing plus Apple's notarization gives
normal distribution outside the App Store; that route requires an eligible Apple
Developer Program account. This preview does not promise a notarized download.
Do not disable Gatekeeper or strip quarantine to make a downloaded app run.

[Apple's signing overview](https://developer.apple.com/developer-id/) ·
[Membership comparison](https://developer.apple.com/support/compare-memberships/)

## Data compatibility

This fork currently keeps Phonon's data paths so existing users retain their
settings and recordings. Do not run Whisplet and Phonon simultaneously; they
share that store and the single-instance lock. Internal executable names remain
`PhononBar` and `phonon`. For the original development install, the installer migrates **Phonon Local.app**
to **Whisplet.app** in `/Applications`, preserving its certificate and bundle ID.
If an old pinned Dock item remains, remove that shortcut and pin the new app.
Previous source installs keep their bundle IDs even after repository ownership
changes. New installs use `com.riadcreates.whisplet`.
