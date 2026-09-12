# Install Whisplet from GitHub

This is a **source-build preview** for Apple Silicon Macs (M1 or later), macOS 14
or later. Your Mac compiles the app. You do not need an app login or paid Apple
Developer membership. Initial setup needs internet access for tools and models;
dictation runs locally once those downloads finish. Allow several GB of free
disk space for models, runtime dependencies and build files.

## One setup command

Paste the whole block below into Terminal. It downloads a complete installer
before running it. Read [the script](../scripts/bootstrap.sh) if you want to
inspect what it does.

```bash
(
  set -e
  whisplet_installer=$(mktemp)
  trap 'rm -f "$whisplet_installer"' EXIT
  curl -fsSL https://raw.githubusercontent.com/riad-creates/whisplet/main/scripts/bootstrap.sh -o "$whisplet_installer"
  /bin/bash "$whisplet_installer"
)
```

The installer:

1. Checks your Mac and opens Apple's Command Line Tools installer if needed.
   **You click Install and review Apple's terms.** Leave Terminal open; setup
   continues automatically after those tools finish installing.
2. Finds usable Rust and uv, including common locations missing from PATH.
   Installs missing tools directly from their official installers. Homebrew is
   unnecessary. It uses the tools immediately without changing shell profiles
   or requiring a Terminal restart.
3. Clones this public repository into `~/Developer/whisplet`, builds the app,
   signs it locally, installs it and opens it. Repeating the command safely
   updates that clone if it is clean and has an upstream.
4. Lets Whisplet handle its Python runtime and first model download on launch.
   **You approve macOS privacy permissions.** No app login is needed.

The first build and downloads take time. Keep the Mac online and allow several
GB of disk space. If setup is interrupted, run the same command again: completed
tool installations, dependency caches and incremental build work are reused.
Apple tool installation waits for up to 45 minutes; after a timeout, complete
Apple's installer and rerun. No licenses are accepted automatically.

## Already downloaded or cloned the source?

Pull the latest changes in your existing clone first, then double-click
**Install Whisplet.command** in Finder, or run:

```bash
bash scripts/install.sh
```

This uses the same automatic dependency setup. If you downloaded a source ZIP,
the installer works, but Git updates require a clone. Do not bypass macOS
security warnings; the Terminal entry point is also available after inspecting
the source. Run `bash scripts/install.sh --check` for a read-only prerequisite
and signing check, or `bash scripts/bootstrap.sh --setup-only` to prepare tools
without building or replacing an app.

## Let an agent install it

Give your coding agent this request:

> Clone https://github.com/riad-creates/whisplet, read its AGENTS.md, and help me build
> and install Whisplet on this Mac using its automatic installer. Keep S1 cleanup off.
> Preserve existing recordings, settings and signing identity if updating.

Your agent can install/build software. You still approve macOS privacy prompts.
Only run installation code from a repository you trust.

## First launch

The default destination for a fresh install is `~/Applications/Whisplet.app`.
Use the exact path printed by the installer for an existing development install.
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
silently replace files you edited. If the app is still running when the build
finishes, the installer waits for you to quit it, then installs and opens the
updated app without making you rebuild again.

Each replacement backs up the previous app under `target/install-backups/` in
your clone. To roll back, quit the app, extract that backup, and restore it to
the same installation path. Do not delete the application-support directory.
Settings, dictionary, recordings, backups and model caches are untouched by
installation and updating. There is no automatic update service yet.

## Where automatic dependencies live

Working tools already on your Mac are reused. If Rust is missing or cannot run,
the installer puts a separate minimal stable Rust toolchain under
`~/.local/share/whisplet/build-tools/{cargo,rustup}`. Missing uv is installed under
`~/.local/share/whisplet/build-tools/bin` (currently uv 0.11.8, matching the tested
app runtime). Existing Rust installations and shell startup files are untouched.
The app bundles uv, so normal dictation does not need a development PATH.

Optional environment settings: `WHISPLET_TOOL_DIR` changes the managed tools
directory; `WHISPLET_SOURCE_DIR` changes the bootstrap clone location;
`WHISPLET_INSTALL_DIR` changes the app destination. Use absolute paths and keep
them consistent on subsequent runs. An explicit `PHONON_UV_BIN` must point to a
working uv executable; unset it to let setup find or install uv automatically.

Official installers: [Rust](https://rust-lang.github.io/rustup/installation/index.html)
and [uv](https://docs.astral.sh/uv/reference/installer/).

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
