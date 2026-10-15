import fcntl
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[2] / 'automation/backup-runner/release-backup-client.py'
FILES = ('prepare_rclone_workdir.py', 'run_restic_container.py', 'restic-lib.sh', 'upload-restic.sh')


class BackupClientReleaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.payload = self.root / 'payload'
        self.target = self.root / 'scripts'
        self.history = self.root / 'history'
        self.lock = self.root / 'backup.lock'
        self.lock.touch()
        self.payload.mkdir()
        self.target.mkdir()
        manifest = {}
        for name in FILES:
            data = ('new-' + name).encode()
            (self.payload / name).write_bytes(data)
            manifest[name] = hashlib.sha256(data).hexdigest()
            (self.target / name).write_text('old-' + name)
        (self.payload / 'manifest.json').write_text(json.dumps(manifest))

    def module(self):
        self.assertTrue(SCRIPT.exists(), 'backup release helper is not implemented')
        spec = importlib.util.spec_from_file_location('release_client', SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def run_release(self, module=None, **kwargs):
        return (module or self.module()).release(self.payload, self.target, self.lock, self.history, **kwargs)

    def assert_old(self):
        for name in FILES:
            self.assertEqual((self.target / name).read_text(), 'old-' + name)

    def test_busy_existing_lock_refuses_without_modification(self):
        module = self.module()
        inode = self.lock.stat().st_ino
        with self.lock.open('r+') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaises(BlockingIOError):
                self.run_release(module)
        self.assert_old()
        self.assertFalse(self.history.exists())
        self.assertEqual(self.lock.stat().st_ino, inode)

    def test_install_preserves_receipt_and_repeat_is_noop(self):
        result = self.run_release()
        self.assertTrue(result['changed'])
        receipt = Path(result['receipt'])
        self.assertEqual(receipt.stat().st_mode & 0o777, 0o700)
        for name in FILES:
            self.assertEqual((self.target / name).read_text(), 'new-' + name)
            self.assertEqual((receipt / name).read_text(), 'old-' + name)
        self.assertFalse(self.run_release()['changed'])
        self.assertEqual(len(list(self.history.iterdir())), 1)

    def test_corrupt_payload_refused_before_mutation(self):
        module = self.module()
        (self.payload / FILES[0]).write_text('corrupt')
        with self.assertRaisesRegex(ValueError, 'checksum'):
            self.run_release(module)
        self.assert_old()
        self.assertFalse(self.history.exists())

    def test_target_symlink_is_not_followed(self):
        module = self.module()
        victim = self.root / 'victim'
        victim.write_text('untouched')
        path = self.target / FILES[0]
        path.unlink()
        path.symlink_to(victim)
        with self.assertRaises((ValueError, OSError)):
            self.run_release(module)
        self.assertEqual(victim.read_text(), 'untouched')

    def test_check_mode_is_read_only(self):
        self.assertTrue(self.run_release(check=True)['changed'])
        self.assert_old()
        self.assertFalse(self.history.exists())

    def test_failed_replacement_rolls_back_previous_files(self):
        module = self.module()
        original = module.os.replace
        failed = False
        def interrupted(src, dst):
            nonlocal failed
            if Path(dst) == self.target / FILES[1] and not failed:
                failed = True
                raise OSError('fixture replacement failure')
            return original(src, dst)
        with patch.object(module.os, 'replace', side_effect=interrupted):
            with self.assertRaisesRegex(OSError, 'fixture'):
                self.run_release(module)
        self.assert_old()
        result = json.loads(next(self.history.glob('*/result.json')).read_text())
        self.assertEqual(result['status'], 'rolled_back')

    def test_rollback_preserves_external_edit_and_records_conflict(self):
        module = self.module()
        original = module.os.replace
        def external_change(src, dst):
            if Path(dst) == self.target / FILES[1]:
                (self.target / FILES[0]).write_text('external edit')
                raise OSError('fixture concurrent writer')
            return original(src, dst)
        with patch.object(module.os, 'replace', side_effect=external_change):
            with self.assertRaises(OSError):
                self.run_release(module)
        self.assertEqual((self.target / FILES[0]).read_text(), 'external edit')
        report = json.loads(next(self.history.glob('*/result.json')).read_text())
        self.assertEqual(report['status'], 'rollback_conflict')
        self.assertEqual(report['conflicts'], [FILES[0]])

    def test_new_helpers_are_installed_without_changing_existing_script_mode(self):
        for name in FILES[:2]:
            (self.target / name).unlink()
        (self.target / 'upload-restic.sh').chmod(0o750)
        result = self.run_release()
        self.assertEqual((self.target / 'upload-restic.sh').stat().st_mode & 0o777, 0o750)
        report = json.loads((Path(result['receipt']) / 'result.json').read_text())
        self.assertIsNone(report['previous'][FILES[0]])
        self.assertEqual((self.target / FILES[0]).stat().st_mode & 0o777, 0o644)

    def test_receipts_and_each_live_replacement_have_directory_durability(self):
        module = self.module()
        self.assertTrue(hasattr(module, 'fsync_directory'), 'directory durability is missing')
        events = []
        original_sync = module.fsync_directory
        original_replace = module.os.replace
        def sync(path):
            events.append(('sync', Path(path)))
            return original_sync(path)
        def replace(src, dst):
            events.append(('replace', Path(dst)))
            return original_replace(src, dst)
        with patch.object(module, 'fsync_directory', side_effect=sync), patch.object(module.os, 'replace', side_effect=replace):
            result = self.run_release(module)
        receipt = Path(result['receipt'])
        first = events.index(('replace', self.target / FILES[0]))
        self.assertIn(('sync', self.history), events[:first])
        self.assertIn(('replace', receipt / 'result.json'), events[:first])
        self.assertIn(('sync', receipt), events[:first])
        for index, (kind, path) in enumerate(events):
            if kind == 'replace':
                self.assertEqual(events[index + 1], ('sync', path.parent))


if __name__ == '__main__':
    unittest.main()
