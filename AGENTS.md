# Whisplet: install, update and develop

Whisplet is an Apple Silicon macOS dictation app based on GPL-3.0 Phonon.
The visible brand is Whisplet; internal `phonon` binary names and data paths are
kept for compatibility. No app account, subscription, cloud inference or paid
Apple Developer membership is required for a local source build.

## Install for a user

1. Read `README.md` and `docs/INSTALL.md`. Inspect scripts before running them.
2. Use the automatic setup in `scripts/bootstrap.sh` / `scripts/install.sh`.
   It checks native arm64 macOS 14+, finds tools outside PATH, and installs
   missing Rust and uv without Homebrew or shell-profile changes. If Apple
   Command Line Tools are missing, it opens Apple's installer and waits for
   the user to approve it. Do not turn missing dependencies into manual chores.
   Do not enroll the user in paid services or accept license terms for them.
3. Run `bash scripts/install.sh --check`. This checks prerequisites and identifies
   the destination/signing strategy without building or replacing the app.
   Missing tools make this read-only check fail; run without --check to set them up.
4. Run `bash scripts/install.sh`. It builds release binaries, creates a signed
   bundle, verifies it, backs up any prior app and installs it. If the existing
   app is running, it waits for the user to quit using its menu, then continues.
   Do not kill a live dictation. It opens the installed app when finished.
5. Open the exact installed path printed by the installer. New installations
   default to `~/Applications/Whisplet.app` and `com.riadcreates.whisplet`.
   The original development install migrates once from `/Applications/Phonon Local.app`
   to `/Applications/Whisplet.app`, retaining `local.tobi.phonon` and its certificate.
   The installer backs up the old bundle first. After migration keep the new path stable.
6. Guide the user through Microphone, Accessibility and Input Monitoring in
   System Settings. These decisions belong to the user. Never modify TCC.db,
   disable Gatekeeper/SIP, strip quarantine, or reset other apps' permissions.
7. Wait for the first model download and warmup. Test a short dictation into a
   disposable text field. Parakeet is used; S1 cleanup starts off. Saved recording
   history is opt-in. Select the actual microphone in Settings.
8. To use F5, select **Settings → Dictation shortcut → F5 hold**. It records until
   release. Apple may map the physical F5 to system Dictation: use Fn+F5 or change
   Keyboard → Keyboard Shortcuts → Function Keys to standard function keys.
   Preserve the user's existing shortcut unless they requested a change.

## Update

In the original clone, run `bash scripts/update.sh`. It refuses a dirty checkout,
uses `git pull --ff-only` on the current branch's upstream, then rebuilds and
installs. Do not reset, force-push or discard user changes to make an update work.
If a branch has no upstream, inspect `git remote -v` and remote branches first.
The public release branch is `main`; don't invent a remote or silently switch a
working development checkout. There is no background auto-updater yet.

The installer touches the app bundle only. Never delete or commit:
- `~/Library/Application Support/Phonon/` (settings, dictionary, recording corpus)
- `~/.phonon/backup`, `~/.cache/huggingface`, uv/Python caches, or app logs
- `.phonon-local-signing-identity` / `.whisplet-signing-identity`
- private keys, tokens, recordings or transcripts from someone's machine

Keep the installed bundle ID, path and signing identity stable. The installer
saves its chosen local identity. A certificate-backed build can retain a stable
identity; ad hoc signing is free but permission grants can need renewal on a
rebuild. Do not silently replace a missing saved certificate with ad hoc signing.
Developer ID/notarization for prebuilt distribution is a separate, optional path.

## Development

- Keep dictation local and account-free. S1 stays optional and off by default;
  preserve explicit saved preferences. Preserve original GPL attribution.
- SwiftUI/AppKit UI: `bar/Sources/`; Rust engine: `crates/`; MLX sidecars:
  `sidecar/`; pinned model/runtime versions: ASR/LLM crate constants.
- Use `swift test --disable-sandbox --package-path bar` for native changes,
  `cargo test --workspace` for engine changes, and the relevant Python tests for
  sidecar changes. Metal inference needs a real Apple Silicon Mac.
- `bash scripts/package-local.sh` rebuilds the established development bundle.
  `bash scripts/install.sh` is the portable build/install entry point.
- Installer changes: `python3 -m unittest discover -s tests -p test_installer.py`
  and `bash scripts/install.sh --check`. Do not uninstall the user's tools to
  simulate a fresh Mac. Keep dependency downloads out of read-only check mode.
- Website is the existing Next.js static export in `website/`. Use `npm ci` if
  dependencies are absent, `npm run lint`, `npm test`, and preserve its lockfile.
- Use fabricated fixtures for previews. Never publish real user recordings or
  transcripts in the website, repository, tests or benchmark reports.
- Work on `codex/…` branches; commit completed changes in coherent increments.
  Describe actual validation and limits; don't claim a physical hotkey or
  microphone was tested based only on unit tests.

## GitHub ownership

This is a personal project. Publish only to `riad-creates/whisplet`; the work
account's copy is not a destination for future pushes. Read `docs/GIT_ACCOUNTS.md`.
Run `gitswitch personal` before GitHub CLI mutations and verify the logged-in
account. Git commits and HTTPS credentials should remain pinned locally to the
personal account even when the global CLI account is switched for other work.
