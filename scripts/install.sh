#!/bin/bash
# Build locally; replace only the app bundle, never recordings, settings or models.
set -euo pipefail
project_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
check_only=false
case "${1:-}" in --check) check_only=true ;; '') ;; *) printf 'Usage: bash scripts/install.sh [--check]\n' >&2; exit 2 ;; esac
fail() { printf '%s\n' "$*" >&2; exit 1; }
source "$project_dir/scripts/bootstrap.sh"
if $check_only; then whisplet_prepare_dependencies check; else whisplet_prepare_dependencies; fi
uv_bin="$PHONON_UV_BIN"

# The visible app name migrates once; the existing signing identity stays stable.
legacy=false
app_name=Whisplet
bundle_id=com.riadcreates.whisplet
install_dir=${WHISPLET_INSTALL_DIR:-"$HOME/Applications"}
identity_file="$project_dir/.whisplet-signing-identity"
previous_app=
if [[ -f "$project_dir/.phonon-local-signing-identity" ]]; then
    for candidate in '/Applications/Phonon Local.app' '/Applications/Whisplet.app'; do
        if [[ -d "$candidate" ]] && [[ $(/usr/libexec/PlistBuddy -c 'Print :CFBundleIdentifier' "$candidate/Contents/Info.plist") == local.tobi.phonon ]]; then
            legacy=true
            bundle_id=local.tobi.phonon
            install_dir=/Applications
            identity_file="$project_dir/.phonon-local-signing-identity"
            previous_app="$candidate"
            break
        fi
    done
fi
[[ "$install_dir" = /* ]] || fail 'WHISPLET_INSTALL_DIR must be an absolute path.'
app_path="$install_dir/$app_name.app"
previous_app=${previous_app:-$app_path}
if [[ "$previous_app" != "$app_path" && -e "$app_path" ]]; then
    fail 'Both the legacy app and Whisplet destination exist. Resolve the duplicate before migrating.'
fi
# Preserve IDs used by earlier source installs, regardless of the repository owner.
if ! $legacy && [[ -f "$app_path/Contents/Info.plist" ]]; then
    prior_id=$(/usr/libexec/PlistBuddy -c 'Print :CFBundleIdentifier' "$app_path/Contents/Info.plist")
    if [[ "$prior_id" == com.tobiwsa.whisplet ]]; then bundle_id="$prior_id"; fi
fi
identity=${PHONON_CODESIGN_IDENTITY:-}
[[ -n "$identity" || ! -f "$identity_file" ]] || identity=$(cat "$identity_file")
if [[ -z "$identity" ]]; then
    identity=$(security find-identity -v -p codesigning 2>/dev/null | awk '/"(Developer ID Application|Apple Development):/ {print $2; exit}')
    identity=${identity:--}
fi
if [[ "$identity" != '-' ]]; then
    security find-identity -v -p codesigning | grep -F -- "$identity" >/dev/null || fail 'The saved signing certificate is unavailable. Restore it before updating; do not silently change identity.'
elif $legacy; then
    fail 'The existing Phonon Local installation requires its persistent signing certificate.'
fi
printf 'Destination: %s\nSigning: %s\n' "$app_path" "$([[ "$identity" == '-' ]] && printf 'ad hoc (no paid membership)' || printf 'saved local certificate')"
if [[ "$identity" == '-' ]]; then
    printf 'Ad hoc builds may need Accessibility and Input Monitoring permission again after updates. Developer ID notarization is not included.\n'
fi
$check_only && exit 0

export PHONON_APP_NAME="$app_name" PHONON_DISPLAY_NAME=Whisplet PHONON_BUNDLE_ID="$bundle_id"
export PHONON_CODESIGN_IDENTITY="$identity" PHONON_UV_BIN="$uv_bin"
bash "$project_dir/scripts/package-bar.sh"
source_app="$project_dir/bar/dist/$app_name.app"
# Wait without killing an in-progress dictation or rebuilding a second time.
for running_path in "$previous_app" "$app_path"; do
    notified=false
    while ps -axo command= | grep -F -- "$running_path/Contents/MacOS/PhononBar" | grep -v grep >/dev/null; do
        if ! $notified; then
            printf '\nBuild complete. Finish any dictation and quit Whisplet (or Phonon Local) from its menu. Installation continues automatically.\n'
            notified=true
        fi
        sleep 2
    done
done
mkdir -p "$install_dir"
staging=$(mktemp -d "$install_dir/.whisplet-install.XXXXXX")
replaced=false
cleanup() {
    if ! $replaced && [[ -d "$staging/previous.app" && ! -e "$previous_app" ]]; then
        mv "$staging/previous.app" "$previous_app"
    fi
    rm -rf "$staging"
}
trap cleanup EXIT
# Finish copying and verifying before replacing anything.
ditto "$source_app" "$staging/new.app"
codesign --verify --deep --strict "$staging/new.app"
if [[ -e "$previous_app" ]]; then
    [[ -d "$previous_app/Contents" && ! -L "$previous_app" ]] || fail 'The destination is not a normal app bundle.'
    existing_id=$(/usr/libexec/PlistBuddy -c 'Print :CFBundleIdentifier' "$previous_app/Contents/Info.plist")
    [[ "$existing_id" == "$bundle_id" ]] || fail 'Destination belongs to a different application; refusing to replace it.'
    backup_dir="$project_dir/target/install-backups"
    mkdir -p "$backup_dir"
    backup_path="$backup_dir/$app_name-$(date +%Y%m%d-%H%M%S)-$$.zip"
    ditto -c -k --sequesterRsrc --keepParent "$previous_app" "$backup_path"
    printf 'Previous app saved: %s\n' "$backup_path"
    mv "$previous_app" "$staging/previous.app"
fi
mv "$staging/new.app" "$app_path"
replaced=true
printf '%s\n' "$identity" > "$identity_file"
printf 'Installed Whisplet. Open: %s\nYour settings, dictionary, recordings and model cache were preserved.\n' "$app_path"
printf 'Opening Whisplet. Approve its macOS permissions and let the first model download finish.\n'
open "$app_path" || printf 'Could not open automatically. Open the app at the path above.\n' >&2
