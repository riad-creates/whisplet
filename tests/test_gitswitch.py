"""Account selection tests use a fake gh executable, never real credentials."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'gitswitch'


class GitSwitchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='gitswitch-test-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / 'repo'
        self.repo.mkdir()
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        self.state = self.root / 'active'
        self.state.write_text('work-user')
        profiles = self.root / 'accounts'
        profiles.write_text('work\twork-user\npersonal\tpersonal-user\n')
        gh = self.bin / 'gh'
        gh.write_text('''#!/bin/bash
set -eu
if [[ "$1 $2" == 'auth switch' ]]; then
  printf '%s' "${6}" > "$GITSWITCH_TEST_STATE"
elif [[ "$1 $2" == 'auth token' ]]; then
  printf 'FAKE_TOKEN_FOR_%s' "${6}"
elif [[ "$1 $2" == 'api user' ]]; then
  account=$(cat "$GITSWITCH_TEST_STATE")
  case "${4}" in
    *tsv*) printf '%s\\t123\\n' "$account" ;;
    *) printf '%s\\n' "$account" ;;
  esac
else
  exit 99
fi
''')
        gh.chmod(0o755)
        self.env = dict(os.environ, PATH=f'{self.bin}:{os.environ["PATH"]}',
                        GITSWITCH_CONFIG=str(profiles), GITSWITCH_TEST_STATE=str(self.state),
                        GIT_CONFIG_GLOBAL='/dev/null', GIT_CONFIG_NOSYSTEM='1')
        self.env.pop('GH_TOKEN', None)
        self.env.pop('GITHUB_TOKEN', None)
        self.git('init', '-q')
        self.git('remote', 'add', 'origin', 'https://github.com/personal-user/example.git')

    def git(self, *args):
        return subprocess.check_output(['git', *args], cwd=self.repo, env=self.env, text=True).strip()

    def run_switch(self, *args, input=None, env=None):
        return subprocess.run([str(SCRIPT), *args], cwd=self.repo, env=env or self.env,
                              input=input, capture_output=True, text=True)

    def test_matching_profile_pins_repository_without_changing_remote(self):
        result = self.run_switch('personal')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.git('config', '--local', 'gitswitch.account'), 'personal-user')
        self.assertEqual(self.git('config', 'user.email'), '123+personal-user@users.noreply.github.com')
        self.assertEqual(self.git('remote', 'get-url', 'origin'), 'https://github.com/personal-user/example.git')

    def test_switching_to_work_preserves_personal_checkout_credentials(self):
        self.assertEqual(self.run_switch('personal').returncode, 0)
        self.assertEqual(self.run_switch('work').returncode, 0)
        self.assertEqual(self.state.read_text(), 'work-user')
        self.assertEqual(self.git('config', '--local', 'gitswitch.account'), 'personal-user')
        result = self.run_switch('credential', 'get', input='protocol=https\nhost=github.com\n\n')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('username=personal-user', result.stdout)
        self.assertIn('FAKE_TOKEN_FOR_personal-user', result.stdout)

    def test_other_hosts_and_store_requests_do_not_return_credentials(self):
        for action, host in [('get', 'example.com'), ('store', 'github.com'), ('erase', 'github.com')]:
            result = self.run_switch('credential', action, input=f'protocol=https\nhost={host}\n\n')
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout, '')

    def test_shell_token_override_and_unknown_profile_leave_identity_unchanged(self):
        for args, env in [(('personal',), dict(self.env, GH_TOKEN='FAKE_OVERRIDE')), (('missing',), self.env)]:
            result = self.run_switch(*args, env=env)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(self.state.read_text(), 'work-user')


if __name__ == '__main__':
    unittest.main()
