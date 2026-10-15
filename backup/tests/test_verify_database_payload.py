import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/verify-database-payload.py'


class PayloadVerificationTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('payload_verify', SCRIPT)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        (self.root / 'postgresql').mkdir()
        self.dump = self.root / 'postgresql/example.dump'
        self.dump.write_bytes(b'native fixture')
        self.hash = hashlib.sha256(self.dump.read_bytes()).hexdigest()
        self.manifest = {'schema_version': 1, 'kind': 'databases', 'status': 'complete',
                         'run_id': 'databases-test', 'artifacts': [
                             {'path': 'postgresql/example.dump', 'sha256': self.hash}]}
        self.save()
        (self.root / 'COMPLETE').write_text('databases-test\n')
        (self.root / 'checksums.sha256').write_text(f'{self.hash}  postgresql/example.dump\n')

    def save(self):
        (self.root / 'manifest.json').write_text(json.dumps(self.manifest))

    def verify(self):
        return self.module.verify(self.root, 'databases-test')

    def test_valid_payload(self):
        report = self.verify()
        self.assertEqual(report['artifacts_verified'], 1)
        self.assertEqual(report['bytes_verified'], 14)
        self.assertEqual(report['scope'], 'database_payload_integrity_only')

    def test_corruption_and_missing_file(self):
        self.dump.write_bytes(b'corrupt')
        with self.assertRaises(ValueError): self.verify()
        self.dump.unlink()
        with self.assertRaises(OSError): self.verify()

    def test_wrong_identity(self):
        (self.root / 'COMPLETE').write_text('other\n')
        with self.assertRaises(ValueError): self.verify()
        (self.root / 'COMPLETE').write_text('databases-test\n')
        self.manifest['run_id'] = 'other'
        self.save()
        with self.assertRaises(ValueError): self.verify()

    def test_duplicate_or_unsafe_artifact(self):
        self.manifest['artifacts'] *= 2
        self.save()
        with self.assertRaises(ValueError): self.verify()
        for name in ('../escape', '/absolute', 'postgresql/../escape'):
            self.manifest['artifacts'] = [{'path': name, 'sha256': self.hash}]
            self.save()
            with self.assertRaises(ValueError): self.verify()

    def test_index_disagreement(self):
        (self.root / 'checksums.sha256').write_text(f'{"0" * 64}  postgresql/example.dump\n')
        with self.assertRaises(ValueError): self.verify()

    def test_symlink_file_or_parent_rejected(self):
        self.dump.rename(self.root / 'real')
        self.dump.symlink_to(self.root / 'real')
        with self.assertRaises(ValueError): self.verify()
        self.dump.unlink()
        (self.root / 'postgresql').rmdir()
        (self.root / 'postgresql').symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(ValueError): self.verify()


if __name__ == '__main__': unittest.main()
