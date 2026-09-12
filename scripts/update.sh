#!/bin/bash
set -euo pipefail
project_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$project_dir"
if [[ -n $(git status --porcelain) ]]; then
    printf 'Save or commit local changes before updating. No files have been changed.\n' >&2
    exit 1
fi
git rev-parse --abbrev-ref '@{upstream}' >/dev/null 2>&1 || {
    printf 'This branch has no upstream. Follow AGENTS.md to select the intended release branch.\n' >&2
    exit 1
}
git pull --ff-only
exec bash "$project_dir/scripts/install.sh"
