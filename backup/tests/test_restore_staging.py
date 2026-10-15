import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/restore-staging.sh'


class RestoreStagingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.calls = self.root / 'calls'
        for name, content in {
            'timeout': '#!/bin/sh\nshift 2\nexec "$@"\n',
            'docker': '#!/bin/sh\n[ "${1:-}" != container ] || exit 0\nif [ "$1" = create ]; then\nprintf "%s\\n" "$@" > "$CALLS"\nprintf "%064d\\n" 1\nexit 0\nfi\nexit "${FAKE_EXIT:-0}"\n',
        }.items():
            path = self.root / name
            path.write_text(content)
            path.chmod(0o700)
        (self.root / 'config').write_text('fake config')
        self.env = {**os.environ, 'PATH': f'{self.root}:{os.environ["PATH"]}',
                    'CALLS': str(self.calls), 'RESTIC_PASSWORD_FILE': str(self.root / 'password'),
                    'RCLONE_CONFIG_FILE': str(self.root / 'config'),
                    'BACKUP_LOCAL_RCLONE_BIN': '/fake/rclone', 'RCLONE_REMOTE': 'fake',
                    'DRIVE_ROOT': 'fake-root', 'RCLONE_CONFIG_WORK_ROOT': str(self.root / 'runtime')}
        self.env.pop('RCLONE_CONFIG_WORKDIR', None)

    def run_restore(self, target, snapshot='a' * 64, exit_code='0'):
        return subprocess.run(['bash', str(SCRIPT), 'databases', snapshot, str(target)],
                              env={**self.env, 'FAKE_EXIT': exit_code}, cwd=self.root,
                              capture_output=True, text=True)

    def test_existing_directory_is_untouched(self):
        target = self.root / 'existing'
        target.mkdir()
        (target / 'sentinel').write_text('keep')
        result = self.run_restore(target)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.calls.exists())
        self.assertEqual((target / 'sentinel').read_text(), 'keep')

    def test_dangling_symlink_is_rejected(self):
        target = self.root / 'link'
        target.symlink_to(self.root / 'absent')
        self.assertNotEqual(self.run_restore(target).returncode, 0)
        self.assertFalse(self.calls.exists())

    def test_relative_destination_and_mutable_snapshot_are_rejected(self):
        self.assertNotEqual(self.run_restore('relative-target').returncode, 0)
        self.assertNotEqual(self.run_restore(self.root / 'fresh', 'latest').returncode, 0)
        self.assertFalse(self.calls.exists())

    def test_new_target_is_private_and_failed_restore_is_preserved(self):
        target = self.root / 'fresh'
        result = self.run_restore(target, exit_code='7')
        self.assertEqual(result.returncode, 7, result.stderr)
        self.assertEqual(target.stat().st_mode & 0o777, 0o700)
        self.assertIn('restore\n' + 'a' * 64, self.calls.read_text())
        self.assertNotEqual(self.run_restore(target).returncode, 0)


if __name__ == '__main__':
    unittest.main()
