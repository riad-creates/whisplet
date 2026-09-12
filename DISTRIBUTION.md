# Whisplet distribution

## Now: GitHub source builds

The repository, `AGENTS.md`, `docs/INSTALL.md` and portable install/update scripts
are the first distribution route. Supported target: Apple Silicon, macOS 14+.
Source builds are locally signed, optionally using a persistent certificate.
No app login, paid developer membership or backend server is required.

`main` is the intended shared release branch. Work in `codex/…` branches and
commit tested changes; publish tested revisions to `main` for source updates.
`bash scripts/update.sh` pulls the tracking branch with `--ff-only` and rebuilds.
This is a manual source update, not an automatic binary updater.

The native interface is Whisplet. Existing Phonon Local installations preserve
bundle ID, signing certificate and data paths while migrating the app bundle name
once to Whisplet.app. Fresh installs use `com.riadcreates.whisplet` in `~/Applications/Whisplet.app`.

## Later: prebuilt app and automatic updates

For a normal downloaded-app experience, obtain Developer ID Application signing
and notarization through an eligible Apple Developer Program account. Sign the
nested helpers and bundle, notarize the packaged artifact and staple the ticket.
The existing `scripts/release-dmg.sh` is an upstream reference and must be adapted
and validated for Whisplet before publishing a binary release.

A future Sparkle updater can fetch a signed update feed and app archives over
HTTPS from static hosting/GitHub Releases. It does not require a Node server or
user accounts. Keep updater signing keys private and preserve the bundle's Apple
signing identity. Sparkle is not integrated in this source-build preview.

The landing page lives in `website/` and links to source installation, not an
upstream Phonon binary. Retain GPL attribution and publish corresponding source
alongside any future distributed Whisplet binaries.

The canonical repository is `riad-creates/whisplet`. See `docs/GIT_ACCOUNTS.md`
for account switching; the work-account copy is not used for future publishing.
