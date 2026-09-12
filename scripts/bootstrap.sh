#!/bin/bash
# Standalone entry point and shared dependency setup for local source builds.
# Download complete installers before running them; never change shell profiles.
set -euo pipefail

whisplet_fail() { printf '\nWhisplet: %s\n' "$*" >&2; exit 1; }

whisplet_check_mac() {
    [[ $(uname -s) == Darwin && $(uname -m) == arm64 ]] ||
        whisplet_fail 'An Apple Silicon Mac is required. Run Terminal natively, not under Rosetta.'
    local mac_version
    mac_version=$(sw_vers -productVersion)
    [[ ${mac_version%%.*} -ge 14 ]] || whisplet_fail 'macOS 14 or later is required.'
}

whisplet_apple_tools_ready() {
    xcode-select -p >/dev/null 2>&1 &&
        xcrun --find swift >/dev/null 2>&1 &&
        xcrun --find clang >/dev/null 2>&1 &&
        xcrun --sdk macosx --show-sdk-path >/dev/null 2>&1
}

whisplet_prepare_apple_tools() {
    if ! whisplet_apple_tools_ready; then
        [[ "$1" != check ]] || whisplet_fail 'Apple Command Line Tools are missing. Run the installer without --check to set them up.'
        if xcode-select -p >/dev/null 2>&1; then
            whisplet_fail 'The selected Apple developer tools are incomplete. Open Xcode to finish its setup, or install Command Line Tools with xcode-select --install, then rerun.'
        fi
        printf '\nApple will open its Command Line Tools installer. Click Install and review its terms.\nLeave this window open; Whisplet continues when Apple finishes. Ctrl+C stops safely.\n'
        xcode-select --install || true
        local attempts=0
        until whisplet_apple_tools_ready; do
            (( attempts < 540 )) || whisplet_fail 'Still waiting for Apple tools. Finish the macOS installer, then rerun this command; completed setup is reused.'
            if (( attempts % 12 == 0 )); then printf 'Waiting for Apple Command Line Tools…\n'; fi
            sleep 5
            attempts=$((attempts + 1))
        done
    fi
    xcrun swift --version >/dev/null 2>&1 || whisplet_fail 'Swift cannot run yet. Complete the Apple developer-tools setup and any license prompts, then rerun.'
    printf 'Apple build tools: ready\n'
}

whisplet_add_tool_paths() {
    # Append common locations: keep a working user-selected toolchain first.
    export PATH="$PATH:${CARGO_HOME:-$HOME/.cargo}/bin:$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin"
    whisplet_tool_dir=${WHISPLET_TOOL_DIR:-"$HOME/.local/share/whisplet/build-tools"}
    [[ "$whisplet_tool_dir" = /* ]] || whisplet_fail 'WHISPLET_TOOL_DIR must be an absolute path.'
}

whisplet_rust_ready() {
    command -v cargo >/dev/null 2>&1 && command -v rustc >/dev/null 2>&1 &&
        cargo --version >/dev/null 2>&1 && rustc --version >/dev/null 2>&1
}

whisplet_download_installer() (
    # A subshell keeps temporary-file cleanup separate from the app install trap.
    set -euo pipefail
    local url="$1"
    shift
    # Keep this subshell variable alive for EXIT, after Bash unwinds locals.
    whisplet_download_dir=$(mktemp -d "${TMPDIR:-/tmp}/whisplet-tool.XXXXXX")
    trap 'rm -rf "$whisplet_download_dir"' EXIT
    curl --fail --show-error --silent --location --proto '=https' --tlsv1.2 \
        --retry 3 --connect-timeout 30 --max-time 300 "$url" -o "$whisplet_download_dir/install.sh" || exit $?
    # Rustup prints manual PATH instructions on success. We already set PATH
    # for this process, so show our own ready message instead. Keep failure logs.
    if /bin/bash "$whisplet_download_dir/install.sh" "$@" > "$whisplet_download_dir/output.log"; then
        return 0
    else
        local result=$?
        cat "$whisplet_download_dir/output.log" >&2
        exit "$result"
    fi
)

whisplet_prepare_rust() {
    if ! whisplet_rust_ready; then
        # Isolate an automatically installed toolchain from the user's Rust setup.
        export CARGO_HOME="$whisplet_tool_dir/cargo" RUSTUP_HOME="$whisplet_tool_dir/rustup"
        export PATH="$CARGO_HOME/bin:$PATH"
        if ! whisplet_rust_ready; then
            [[ "$1" != check ]] || whisplet_fail 'Rust is missing. Run the installer without --check to install it automatically.'
            printf '\nInstalling Rust for Whisplet (no shell configuration changes)…\n'
            mkdir -p "$whisplet_tool_dir"
            # A separate Rust installation may exist outside PATH. This managed
            # toolchain deliberately coexists with it instead of replacing it.
            RUSTUP_INIT_SKIP_PATH_CHECK=yes whisplet_download_installer https://sh.rustup.rs \
                -y --profile minimal --default-toolchain stable --no-modify-path
            whisplet_rust_ready || whisplet_fail 'Rust setup did not complete. Check the error above and rerun; installed tools are reused.'
        fi
    fi
    printf 'Rust: %s\n' "$(rustc --version)"
}

whisplet_find_uv() {
    local candidate
    if [[ -n ${PHONON_UV_BIN:-} ]]; then
        [[ -x "$PHONON_UV_BIN" ]] && "$PHONON_UV_BIN" --version >/dev/null 2>&1 ||
            whisplet_fail 'PHONON_UV_BIN points to an unavailable uv executable. Correct it or unset it.'
        return
    fi
    for candidate in "$(command -v uv || true)" "$whisplet_tool_dir/bin/uv" \
        '/Applications/Whisplet.app/Contents/Helpers/uv' \
        '/Applications/Phonon Local.app/Contents/Helpers/uv' \
        "$HOME/Applications/Whisplet.app/Contents/Helpers/uv"; do
        if [[ -x "$candidate" ]] && "$candidate" --version >/dev/null 2>&1; then
            export PHONON_UV_BIN="$candidate"
            return 0
        fi
    done
    return 1
}

whisplet_prepare_uv() {
    if ! whisplet_find_uv; then
        [[ "$1" != check ]] || whisplet_fail 'uv is missing. Run the installer without --check to install it automatically.'
        printf '\nInstalling uv for Whisplet…\n'
        mkdir -p "$whisplet_tool_dir"
        UV_UNMANAGED_INSTALL="$whisplet_tool_dir/bin" whisplet_download_installer \
            https://astral.sh/uv/0.11.8/install.sh
        whisplet_find_uv || whisplet_fail 'uv setup did not complete. Check the error above and rerun.'
    fi
    printf 'Python manager: %s\n' "$("$PHONON_UV_BIN" --version)"
}

whisplet_prepare_dependencies() {
    local mode="${1:-install}"
    whisplet_check_mac
    whisplet_add_tool_paths
    whisplet_prepare_apple_tools "$mode"
    whisplet_prepare_rust "$mode"
    whisplet_prepare_uv "$mode"
}

whisplet_bootstrap() {
    case "${1:-}" in
        --check) whisplet_prepare_dependencies check; return ;;
        --setup-only) whisplet_prepare_dependencies; return ;;
        '') ;;
        *) whisplet_fail 'Usage: bash bootstrap.sh [--check | --setup-only]' ;;
    esac
    whisplet_prepare_dependencies
    local clone_dir=${WHISPLET_SOURCE_DIR:-"$HOME/Developer/whisplet"} origin
    [[ "$clone_dir" = /* ]] || whisplet_fail 'WHISPLET_SOURCE_DIR must be an absolute path.'
    if [[ -e "$clone_dir" ]]; then
        [[ -d "$clone_dir/.git" ]] || whisplet_fail "Destination already exists and is not a Git clone: $clone_dir. Use its Install Whisplet.command, or choose another WHISPLET_SOURCE_DIR."
        origin=$(git -C "$clone_dir" remote get-url origin)
        case "$origin" in
            https://github.com/riad-creates/whisplet|https://github.com/riad-creates/whisplet.git|git@github.com:riad-creates/whisplet.git) ;;
            *) whisplet_fail "The existing directory belongs to another repository: $clone_dir. Nothing was overwritten." ;;
        esac
        exec /bin/bash "$clone_dir/scripts/update.sh"
    fi
    mkdir -p "$(dirname "$clone_dir")"
    printf '\nDownloading Whisplet source to %s…\n' "$clone_dir"
    git clone --branch main https://github.com/riad-creates/whisplet.git "$clone_dir"
    exec /bin/bash "$clone_dir/scripts/install.sh"
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then whisplet_bootstrap "$@"; fi
