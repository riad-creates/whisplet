"""Exercise installer failure/retry paths without changing the host's tools."""

import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class DependencySetupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="whisplet setup test ")
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.env = dict(os.environ, WHISPLET_TOOL_DIR=str(self.folder / "tools"))
        self.env.pop("PHONON_UV_BIN", None)

    def run_shell(self, code):
        return subprocess.run(
            ["/bin/bash", "-c", f"source {shlex.quote(str(ROOT / 'scripts/bootstrap.sh'))}\n{code}"],
            env=self.env, text=True, capture_output=True, timeout=15,
        )

    def test_sourcing_does_not_install_or_create_directories(self):
        result = self.run_shell(":")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_check_does_not_launch_apple_installer(self):
        result = self.run_shell("""
whisplet_apple_tools_ready() { return 1; }
xcode-select() { echo 'UNEXPECTED INSTALL'; }
whisplet_prepare_apple_tools check
""")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Apple Command Line Tools are missing", result.stderr)
        self.assertNotIn("UNEXPECTED", result.stdout)

    def test_apple_install_continues_without_rerunning_command(self):
        result = self.run_shell("""
ready=false
whisplet_apple_tools_ready() { $ready; }
xcode-select() { [[ "$1" == --install ]]; }
sleep() { ready=true; }
xcrun() { return 0; }
whisplet_prepare_apple_tools install
echo RESUMED
""")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("RESUMED", result.stdout)

    def test_missing_rust_check_is_read_only(self):
        result = self.run_shell("""
whisplet_add_tool_paths
whisplet_rust_ready() { return 1; }
whisplet_prepare_rust check
""")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Rust is missing", result.stderr)
        self.assertFalse((self.folder / "tools").exists())

    def test_missing_uv_check_is_read_only(self):
        result = self.run_shell("""
whisplet_add_tool_paths
whisplet_find_uv() { return 1; }
whisplet_prepare_uv check
""")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("uv is missing", result.stderr)
        self.assertFalse((self.folder / "tools").exists())

    def test_existing_rust_outside_path_is_found_without_installing(self):
        cargo_dir = self.folder / "existing cargo"
        binaries = cargo_dir / "bin"
        binaries.mkdir(parents=True)
        for name in ("cargo", "rustc"):
            binary = binaries / name
            binary.write_text("#!/bin/bash\necho existing-rust\n")
            binary.chmod(0o755)
        self.env["CARGO_HOME"] = str(cargo_dir)
        result = self.run_shell("""
export PATH=/usr/bin:/bin:/usr/sbin:/sbin
whisplet_add_tool_paths
whisplet_prepare_rust install
""")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("existing-rust", result.stdout)
        self.assertFalse((self.folder / "tools").exists())

    def test_failed_installer_retains_diagnostic_output(self):
        result = self.run_shell("""
curl() {
    while [[ "$1" != -o ]]; do shift; done
    printf 'echo useful-error-message\\nexit 42\\n' > "$2"
}
whisplet_download_installer https://example.invalid/install.sh
""")
        self.assertEqual(result.returncode, 42)
        self.assertIn("useful-error-message", result.stderr)

    def test_download_failure_never_executes_partial_script(self):
        self.env["TEST_MARKER"] = str(self.folder / "should-not-exist")
        result = self.run_shell("""
curl() {
    while [[ "$1" != -o ]]; do shift; done
    printf 'touch "$TEST_MARKER"\\n' > "$2"
    return 22
}
whisplet_download_installer https://example.invalid/install.sh
""")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(Path(self.env["TEST_MARKER"]).exists())

    def test_fresh_tools_are_usable_immediately_and_reused(self):
        # Pretend the only working executables are those created by downloaded
        # installers. The real host PATH and home are never changed.
        result = self.run_shell("""
whisplet_add_tool_paths
whisplet_rust_ready() {
    [[ -x "$whisplet_tool_dir/cargo/bin/cargo" ]] &&
        [[ -x "$whisplet_tool_dir/cargo/bin/rustc" ]] &&
        [[ "$(command -v cargo)" == "$whisplet_tool_dir/cargo/bin/cargo" ]]
}
whisplet_find_uv() {
    if [[ -x "$whisplet_tool_dir/bin/uv" ]]; then
        export PHONON_UV_BIN="$whisplet_tool_dir/bin/uv"
        return 0
    fi
    return 1
}
curl() {
    while [[ "$1" != -o ]]; do shift; done
    cat > "$2" <<'INSTALLER'
set -eu
if [[ -n "${UV_UNMANAGED_INSTALL:-}" ]]; then
    mkdir -p "$UV_UNMANAGED_INSTALL"
    printf '#!/bin/bash\\necho uv-test\\n' > "$UV_UNMANAGED_INSTALL/uv"
    chmod +x "$UV_UNMANAGED_INSTALL/uv"
else
    [[ "$*" == '-y --profile minimal --default-toolchain stable --no-modify-path' ]]
    mkdir -p "$CARGO_HOME/bin"
    for binary in cargo rustc; do
        printf '#!/bin/bash\\necho rust-test\\n' > "$CARGO_HOME/bin/$binary"
        chmod +x "$CARGO_HOME/bin/$binary"
    done
fi
INSTALLER
}
whisplet_prepare_rust install
whisplet_prepare_uv install
cargo --version
"$PHONON_UV_BIN" --version
# A second run must not download anything.
curl() { echo UNEXPECTED_DOWNLOAD >&2; return 1; }
whisplet_prepare_rust install
whisplet_prepare_uv install
""")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("rust-test", result.stdout)
        self.assertIn("uv-test", result.stdout)
        self.assertNotIn("UNEXPECTED", result.stderr)

    def test_invalid_uv_override_is_not_silently_replaced(self):
        self.env["PHONON_UV_BIN"] = str(self.folder / "missing-uv")
        result = self.run_shell("whisplet_add_tool_paths\nwhisplet_prepare_uv install")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("PHONON_UV_BIN", result.stderr)

    def test_bootstrap_refuses_unrelated_existing_directory(self):
        source = self.folder / "existing directory"
        source.mkdir()
        keep = source / "keep.txt"
        keep.write_text("user work")
        self.env["WHISPLET_SOURCE_DIR"] = str(source)
        result = self.run_shell("""
whisplet_prepare_dependencies() { :; }
whisplet_bootstrap
""")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("already exists", result.stderr)
        self.assertEqual(keep.read_text(), "user work")


if __name__ == "__main__":
    unittest.main()
