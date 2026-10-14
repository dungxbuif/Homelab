import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / 'scripts/homepage-release-ssh-guard.py'
DIGEST = 'sha256:' + 'a' * 64


class GuardTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('release_guard', PATH)
        self.guard = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.guard)

    def test_invalid_commands_never_execute(self):
        for command in ['', 'id', 'homepage-release', 'homepage-release ' + DIGEST + ' extra',
                        'homepage-release ' + DIGEST + ';id', 'homepage-release ' + DIGEST + '\n',
                        ' homepage-release ' + DIGEST, 'homepage-release sha256:' + 'A' * 64,
                        'scp -t /tmp/x', 'homepage-release $(id)']:
            with self.subTest(command=command), patch.dict(self.guard.os.environ,
                    {'SSH_ORIGINAL_COMMAND': command}, clear=True), \
                    patch.object(self.guard.os, 'execve') as execute, \
                    patch.object(self.guard.sys, 'argv', [str(PATH)]):
                self.assertEqual(self.guard.main(), 2)
                execute.assert_not_called()

    def test_valid_command_has_fixed_owner_and_clean_environment(self):
        with patch.dict(self.guard.os.environ, {'SSH_ORIGINAL_COMMAND': 'homepage-release ' + DIGEST,
                'PYTHONPATH': '/untrusted', 'LD_PRELOAD': '/untrusted', 'PATH': '/untrusted'}, clear=True), \
                patch.object(self.guard.os, 'execve') as execute, \
                patch.object(self.guard.sys, 'argv', [str(PATH)]):
            self.guard.main()
            execute.assert_called_once_with('/usr/bin/sudo.ws',
                ['/usr/bin/sudo.ws', '-n', '-u', 'dungxbuif',
                 '/usr/local/libexec/homelab-homepage-release', DIGEST],
                {'PATH': '/usr/sbin:/usr/bin:/sbin:/bin', 'LANG': 'C.UTF-8'})

    def test_direct_guard_arguments_are_rejected(self):
        with patch.object(self.guard.sys, 'argv', [str(PATH), 'ignored']), \
                patch.object(self.guard.os, 'execve') as execute:
            self.assertEqual(self.guard.main(), 2)
            execute.assert_not_called()


if __name__ == '__main__':
    unittest.main()
