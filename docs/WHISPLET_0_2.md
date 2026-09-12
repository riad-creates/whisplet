# Whisplet 0.2 source-build preview

## Included

- F5 hold-to-record as a selectable shortcut, with repeat/release handling and
  independent registration. Existing shortcuts remain selectable.
- Light native interface, violet wave-and-cursor mark, updated app icon and
  recording pill, recent transcript cards and recording playback.
- S1-mini off for fresh settings; explicit existing choices are retained.
- Source installer, fast-forward-only update command and AGENTS.md. No app
  account, paid developer enrollment or server is needed for local source builds.
- Static landing page with source installation and accurate preview limitations.

## Validation, September 12, 2026

- 47 native Swift tests passed. Rust workspace tests (34) passed for the earlier
  shortcut/default change; the visual and installer changes do not modify Rust.
- Production release bundle built, signed with the existing development identity
  and installed using the portable installer. The old app was backed up first.
- Required macOS permissions remained Granted after both installed UI updates.
  F5 selection and cleanup-off preference survived restart. Native Dictation and
  Settings were visually inspected in the running app.
- A separate fresh source checkout built and installed successfully with ad hoc
  signing into a temporary directory, without using a distribution certificate.
  Its bundled signature was verified; this does not simulate a fresh user's TCC
  permissions or replace testing on another Mac.
- Website lint, TypeScript/production export and rendered-output checks passed.
  Private hosted deployment completed successfully.

## Limits

Physical F5 hold/release and spoken dictation still need a user smoke test on
this keyboard, especially if macOS maps F5 to Apple Dictation. Fn+F5 or standard
function keys may be needed. Ad hoc builds can need renewed permissions after
updates. No notarized Whisplet download or automatic binary updater is shipped.
The private repository must be made public or shared before another account can
clone it; this does not add a login requirement to the app itself.

The existing local installation keeps its Phonon Local bundle path, bundle ID,
certificate and data directory for compatibility. Internal binary names also
remain unchanged. No personal recordings, model caches or signing secrets are
included in the repository or landing page.

## Personal repository and app-name migration

The current publishing target is `riad-creates/whisplet`. The earlier work-account
copy remains unchanged; ownership transfer was not performed. The origin remote,
future commit identity and Git HTTPS credentials are pinned to the personal account.
`gitswitch work`, `gitswitch personal` and `gitswitch status` switch/inspect the
saved CLI accounts. Four isolated tests passed, and a real private-repository
read succeeded while the CLI was switched to work, using the checkout's pinned
personal credentials. The CLI was returned to personal afterward.

The installed bundle migrated to `/Applications/Whisplet.app`. Its signature
satisfies the pre-migration requirement; required permissions, F5 and cleanup-off
survived relaunch. The Dock's recent-app entry now labels it **Whisplet** and
points to the new bundle path. The previous app was saved as a zip backup by
the installer. The installer's subsequent preflight resolves the new path with
the same persistent certificate. Fresh source installs now use
`com.riadcreates.whisplet`; existing installations retain their bundle IDs.

The landing page's installation links now target the personal repository. Its
lint and production/static-output tests passed again.
