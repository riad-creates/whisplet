#!/bin/bash
set -euo pipefail

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
project_dir=$(cd "$script_dir/.." && pwd)
identity=${PHONON_CODESIGN_IDENTITY:-}
if [[ -z "$identity" && -f "$project_dir/.phonon-local-signing-identity" ]]; then
	identity=$(cat "$project_dir/.phonon-local-signing-identity")
fi
if [[ -z "$identity" || "$identity" == "-" ]]; then
	printf 'Phonon Local needs a persistent signing certificate. Set PHONON_CODESIGN_IDENTITY or save its fingerprint in .phonon-local-signing-identity.\n' >&2
	exit 1
fi

export PHONON_APP_NAME='Phonon Local'
export PHONON_BUNDLE_ID='local.tobi.phonon'
export PHONON_CODESIGN_IDENTITY="$identity"
export PHONON_UV_BIN=${PHONON_UV_BIN:-'/Applications/Phonon Local.app/Contents/Helpers/uv'}
exec bash "$script_dir/package-bar.sh"
