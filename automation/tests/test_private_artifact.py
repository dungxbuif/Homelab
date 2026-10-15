import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/write-private-artifact.py'


class PrivateArtifactTests(unittest.TestCase):
    def module(self):
        self.assertTrue(SCRIPT.exists(), 'private descriptor-based writer missing')
        spec = importlib.util.spec_from_file_location('private_artifact', SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_private_new_file_and_no_overwrite(self):
        module = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp).resolve() / 'report.json'
            module.write_artifact(target, b'{"ok":true}')
            self.assertEqual(target.stat().st_mode & 0o777, 0o600)
            self.assertEqual(json.loads(target.read_text()), {'ok': True})
            with self.assertRaises(FileExistsError):
                module.write_artifact(target, b'{}')
            self.assertEqual(json.loads(target.read_text()), {'ok': True})

    def test_writable_ancestor_rejected(self):
        module = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            ancestor = Path(tmp).resolve() / 'unsafe'
            ancestor.mkdir(mode=0o777)
            ancestor.chmod(0o777)
            parent = ancestor / 'private'
            parent.mkdir(mode=0o700)
            with self.assertRaises(ValueError):
                module.write_artifact(parent / 'report.json', b'{}')
            self.assertEqual(list(parent.iterdir()), [])

    def test_parent_swap_cannot_redirect_output(self):
        module = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            parent = root / 'private'
            parent.mkdir(mode=0o700)
            original = module.os.open
            def swap(path, flags, *args, **kwargs):
                if path == 'report.json':
                    parent.rename(root / 'moved')
                    parent.mkdir(mode=0o700)
                return original(path, flags, *args, **kwargs)
            with patch.object(module.os, 'open', side_effect=swap):
                with self.assertRaisesRegex(ValueError, 'directory changed'):
                    module.write_artifact(parent / 'report.json', b'{}')
            self.assertEqual(list(parent.iterdir()), [])
            self.assertEqual(list((root / 'moved').iterdir()), [])


if __name__ == '__main__':
    unittest.main()
