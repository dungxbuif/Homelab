from pathlib import Path
import os
import stat
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/prepare_rclone_workdir.py'


class RcloneWorkdirTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.source = self.root / 'source.conf'
        self.source.write_text('dummy-token-only')

    def tearDown(self):
        self.temp.cleanup()

    def prepare(self, *args):
        return subprocess.run(['python3', str(SCRIPT), str(self.source), *map(str, args)],
                              capture_output=True, text=True)

    def test_private_copy_preserves_source(self):
        result = self.prepare('--root', self.root / 'staging/runtime')
        self.assertEqual(result.returncode, 0, result.stderr)
        work = Path(result.stdout.strip())
        self.assertEqual(work.parent, self.root / 'staging/runtime')
        self.assertEqual(stat.S_IMODE(work.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE((work / 'rclone.conf').stat().st_mode), 0o600)
        self.assertEqual((work / 'rclone.conf').read_text(), 'dummy-token-only')
        self.assertEqual(self.source.read_text(), 'dummy-token-only')

    def test_symlinked_root_rejected(self):
        (self.root / 'alias').symlink_to(self.root, target_is_directory=True)
        result = self.prepare('--root', self.root / 'alias/new')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.root / 'new').exists())

    def test_failed_copy_removes_new_work_directory(self):
        self.source.unlink()
        parent = self.root / 'runtime'
        result = self.prepare('--root', parent)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('source.conf', result.stderr)
        self.assertEqual(list(parent.iterdir()), [])

    def test_unsafe_root_not_chmodded_or_used(self):
        unsafe = self.root / 'unsafe'
        unsafe.mkdir(mode=0o777)
        unsafe.chmod(0o777)
        result = self.prepare('--root', unsafe)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('unsafe directory', result.stderr)
        self.assertEqual(stat.S_IMODE(unsafe.stat().st_mode), 0o777)
        self.assertEqual(list(unsafe.iterdir()), [])

    def test_inherited_config_symlink_does_not_overwrite_victim(self):
        work = self.root / 'inherited'
        work.mkdir(mode=0o700)
        victim = self.root / 'victim'
        victim.write_text('unchanged')
        (work / 'rclone.conf').symlink_to(victim)
        result = self.prepare('--existing', work)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(victim.read_text(), 'unchanged')
        self.assertFalse((work / 'rclone.conf').is_symlink())

    @unittest.skipUnless(os.geteuid() == 0, 'foreign ownership fixture requires root')
    def test_foreign_owned_parent_rejected_before_copy(self):
        foreign = self.root / 'attacker'
        foreign.mkdir(mode=0o700)
        os.chown(foreign, 12345, 12345)
        try:
            result = self.prepare('--root', foreign / 'rclone')
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('unsafe directory', result.stderr)
            self.assertFalse((foreign / 'rclone').exists())
            self.assertEqual(foreign.stat().st_uid, 12345)
        finally:
            os.chown(foreign, 0, 0)


if __name__ == '__main__':
    unittest.main()
