#!/bin/bash
# Build locally; replace only the app bundle, never recordings, settings or models.
set -euo pipefail
project_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
check_only=false
case "${1:-}" in --check) check_only=true ;; '') ;; *) printf 'Usage: bash scripts/install.sh [--check]\n' >&2; exit 2 ;; esac
fail() { printf '%s\n' "$*" >&2; exit 1; }
[[ $(uname -s) == Darwin && $(uname -m) == arm64 ]] || fail 'Whisplet needs an Apple Silicon Mac. Run Terminal natively, not under Rosetta.'
mac_version=$(sw_vers -productVersion)
[[ ${mac_version%%.*} -ge 14 ]] || fail 'Whisplet needs macOS 14 or later.'
xcrun --find swift >/dev/null 2>&1 || fail 'Install Apple Command Line Tools: xcode-select --install'
command -v cargo >/dev/null || fail 'Install Rust using https://rustup.rs, then open a new terminal.'
uv_bin=${PHONON_UV_BIN:-$(command -v uv || true)}
if [[ -z "$uv_bin" && -x '/Applications/Phonon Local.app/Contents/Helpers/uv' ]]; then
    uv_bin='/Applications/Phonon Local.app/Contents/Helpers/uv'
fi
[[ -x "$uv_bin" ]] || fail 'Install uv: brew install uv (or follow https://docs.astral.sh/uv/getting-started/installation/).'

# Preserve the original development install's path, certificate and permissions.
legacy=false
if [[ -f "$project_dir/.phonon-local-signing-identity" && -d '/Applications/Phonon Local.app' ]]; then
    legacy=true
    app_name='Phonon Local'
    bundle_id='local.tobi.phonon'
    install_dir=/Applications
    identity_file="$project_dir/.phonon-local-signing-identity"
else
    app_name=Whisplet
    bundle_id=com.tobiwsa.whisplet
    install_dir=${WHISPLET_INSTALL_DIR:-"$HOME/Applications"}
    identity_file="$project_dir/.whisplet-signing-identity"
fi
[[ "$install_dir" = /* ]] || fail 'WHISPLET_INSTALL_DIR must be an absolute path.'
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
app_path="$install_dir/$app_name.app"
printf 'Destination: %s\nSigning: %s\n' "$app_path" "$([[ "$identity" == '-' ]] && printf 'ad hoc (no paid membership)' || printf 'saved local certificate')"
if [[ "$identity" == '-' ]]; then
    printf 'Ad hoc builds may need Accessibility and Input Monitoring permission again after updates. Developer ID notarization is not included.\n'
fi
$check_only && exit 0

export PHONON_APP_NAME="$app_name" PHONON_DISPLAY_NAME=Whisplet PHONON_BUNDLE_ID="$bundle_id"
export PHONON_CODESIGN_IDENTITY="$identity" PHONON_UV_BIN="$uv_bin"
bash "$project_dir/scripts/package-bar.sh"
source_app="$project_dir/bar/dist/$app_name.app"
# Fail before touching the installed bundle if it is still running.
if ps -axo command= | grep -F -- "$app_path/Contents/MacOS/PhononBar" | grep -v grep >/dev/null; then
    fail 'Build complete. Quit Whisplet (or Phonon Local) from its menu, then run this installer again.'
fi
mkdir -p "$install_dir"
staging=$(mktemp -d "$install_dir/.whisplet-install.XXXXXX")
replaced=false
cleanup() {
    if ! $replaced && [[ -d "$staging/previous.app" && ! -e "$app_path" ]]; then
        mv "$staging/previous.app" "$app_path"
    fi
    rm -rf "$staging"
}
trap cleanup EXIT
# Finish copying and verifying before replacing anything.
ditto "$source_app" "$staging/new.app"
codesign --verify --deep --strict "$staging/new.app"
if [[ -e "$app_path" ]]; then
    [[ -d "$app_path/Contents" && ! -L "$app_path" ]] || fail 'The destination is not a normal app bundle.'
    existing_id=$(/usr/libexec/PlistBuddy -c 'Print :CFBundleIdentifier' "$app_path/Contents/Info.plist")
    [[ "$existing_id" == "$bundle_id" ]] || fail 'Destination belongs to a different application; refusing to replace it.'
    backup_dir="$project_dir/target/install-backups"
    mkdir -p "$backup_dir"
    backup_path="$backup_dir/$app_name-$(date +%Y%m%d-%H%M%S)-$$.zip"
    ditto -c -k --sequesterRsrc --keepParent "$app_path" "$backup_path"
    printf 'Previous app saved: %s\n' "$backup_path"
    mv "$app_path" "$staging/previous.app"
fi
mv "$staging/new.app" "$app_path"
replaced=true
printf '%s\n' "$identity" > "$identity_file"
printf 'Installed Whisplet. Open: %s\nYour settings, dictionary, recordings and model cache were preserved.\n' "$app_path"
