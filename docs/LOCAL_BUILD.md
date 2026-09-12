# Phonon Local: S1-mini build

Installed at `/Applications/Phonon Local.app`, bundle ID `local.tobi.phonon`, based on upstream Phonon 0.1.7. The original `/Applications/Phonon.app` is retained. Both use the Phonon data directory and single-instance lock.

Settings → AI cleanup is on. On runs Parakeet followed by S1-mini by Superwhisper; off unloads the cleanup model and passes through the Parakeet transcript. The setting persists across launches, and changes wait until the active dictation finishes.

S1-mini by Superwhisper uses the pinned MLX 4-bit conversion at `5cbd7aec3401144f88a331d385c40b65fd2548eb`. The exact trained system prompt and control line are used, with thinking disabled. Cleanup supports English. Screen context and fuzzy dictionary prompts are unavailable; explicit replacements still apply with cleanup on.

Long text is split at sentence boundaries where possible, then whitespace boundaries, into 768-token transcript chunks. There is no whole-transcript output ceiling. A chunk that hits its generation budget or returns blank retains its source text. This avoids truncating the transcript because of the output cap; it cannot guarantee that every model edit preserves meaning. Parakeet's audio buffering and final full-WAV transcription are unchanged.

## Validation on September 10, 2026

Machine: Apple M1 Pro, 16 GB unified memory.

- Rust workspace: 34 tests passed.
- Swift: 41 tests passed; final app also compiled successfully.
- Python: existing ASR tests and six cleanup tests passed.
- Engine integration: test WAV transcribed through Parakeet, S1-mini warmup and cleanup passed, switching off terminated both uv and its Python model child, and a 7,000-word bypass preserved the text exactly.
- Installed app: toggled cleanup off and on through the native UI; checked persisted settings and confirmed no cleanup process remained while off.
- Real S1-mini cleanup: four cached-model short requests took 185–329 ms. The initial cold generation in an earlier run took about 1.16 seconds, excluding download.
- Long stress test: 1,679 input tokens / approximately 1,450 output words took 16.36 seconds across three chunks. One repetitive chunk reached the output budget and fell back to its original text. All 80 numbered project references and the final “Blue Harbor” sentence were retained.
- MLX allocated-memory peak during that S1-mini-only test: 1.31 GB. Active MLX allocations after completion: 335 MB. These numbers exclude Parakeet, Python overhead, app UI, and other processes; they are not total app RAM measurements.
- App bundle signature verified with `codesign --verify --deep --strict`.

Live microphone capture and insertion in the new app still need a user test after granting this app Microphone, Accessibility, and Input Monitoring access. Screen Recording is unnecessary for this build.

The unused Gemma cache was moved to `~/.Trash/Phonon-Gemma-model-2026-09-10`. It remains recoverable and continues occupying disk space until Trash is emptied. The original app will download Gemma again if launched without restoring that cache.

## Signing and permissions

The earlier ad hoc builds used a designated requirement containing only the current executable's code hash. Recompilation changed that identity and invalidated permission matching. On September 11, 2026, the local build was switched to the existing Apple Development certificate in this Mac's keychain. Apple describes this distinction in [TN3127: Code Signing Requirements](https://developer.apple.com/documentation/technotes/tn3127-inside-code-signing-requirements).

Run `bash scripts/package-local.sh` for future updates. It reads the certificate fingerprint from the git-ignored `.phonon-local-signing-identity`, fixes the existing app name and bundle ID, and signs the app and its helpers with the same certificate. It stops if no persistent identity is configured. The base packager also refuses ad hoc signing for `local.tobi.phonon`. No private key is stored in the repository.

Switching from ad hoc signing to this certificate may require a final grant. After installing the signed build, quit Phonon Local completely, remove and re-add its entry in Accessibility and Input Monitoring if a stale entry remains, and reopen it. Use `/Applications/Phonon Local.app`, not the original app or a backup. Grant microphone access from Home if requested. Screen Recording is unnecessary for S1-mini dictation. These permission changes are performed by the user; the build does not edit macOS's permission database.

Future builds must keep the same signing identity, bundle ID, and installation path. This fixes the build identity mismatch; it cannot guarantee against permission resets from certificate changes, macOS changes, or manual revocation.

Validation: packaged and launched the Apple Development-signed app; verified its installed signature; signed a disposable variant with changed bundle content and confirmed the code hashes differ while both satisfy the exact same certificate-based designated requirement. Both local build entry points reject explicit ad hoc signing. Actual permission persistence across an update still requires the user to grant this new identity once.

### When Settings shows enabled but the app reports denied

On September 11, macOS logs confirmed `Failed to match existing code requirement` for Accessibility and ListenEvent: the enabled records still contained an older ad hoc code hash, while the running app had the new certificate-based identity. Refreshing the app did not repair those records.

With Phonon Local fully quit, these app-specific resets succeeded:

```sh
tccutil reset Accessibility local.tobi.phonon
tccutil reset ListenEvent local.tobi.phonon
```

Reopen the app and System Settings, then approve the current app in both panes. These commands clear existing decisions; they do not grant access. Microphone access and other apps' permissions are unaffected. See [Apple's reset documentation](https://developer.apple.com/documentation/xcode/resetting-access-to-protected-resources-in-macos). Do not reset all services or all apps for this issue.

## Recording indicator update (September 11)

The floating pill now sits above the Dock using the selected screen's usable frame. It rechecks placement after display and Space changes and once per second for Dock resizing. The idle pill has a visible outline; recording expands it into a waveform of recent microphone levels; processing shows a rotating indicator before returning to idle. Reduced Motion disables the size and waveform animations and rotation.

Validation: 43 native tests passed, including bottom-Dock placement on an offset display and side-Dock/auto-hide geometry. All three production SwiftUI states were rendered to local previews in `target/dock-preview`. The signed UI update retained the previous designated requirement; Microphone, Accessibility, and Input Monitoring remained Granted after installation. Speech sidecars were unchanged. Actual speech-driven animation still warrants a manual recording check with the physical shortcut.

The previous app is preserved in `bar/dist/Phonon Local before waveform 2026-09-11.app`.

## Recording controls and microphone diagnosis (September 11)

The app and status menus now offer Start Recording / Stop Recording (Command-Shift-R). Explicit menu actions work independently of the chosen physical shortcut. The pill reports “No speech detected,” “No microphone audio,” or “Microphone unavailable” instead of silently returning to idle for those failures.

Validation: all 44 native tests passed, including menu actions under every shortcut mode. The updated app was installed with the same designated signing requirement, and Microphone, Accessibility, and Input Monitoring stayed Granted. The native menu was exercised to start and stop a recording. The prior installed build is saved in `bar/dist/Phonon Local before recording controls 2026-09-11.zip`.

Three failed captures contained almost no voice and also returned empty transcripts when replayed directly through Parakeet without the preliminary speech gate. Phonon was recording the built-in microphone, while the user confirmed speaking through their WH-1000XM6 headset. The saved priority is now WH-1000XM6, then MacBook Pro Microphone. The headset initially appeared in CoreAudio but was no longer available after restart, so end-to-end headset dictation remains to be checked after reconnection. No speech threshold or model changes were made for this diagnosis.
