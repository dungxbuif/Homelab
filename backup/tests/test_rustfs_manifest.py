#!/usr/bin/env python3
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("rustfs_export", ROOT / "automation/rustfs-backup/export-buckets.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)
RESTORE_SPEC = importlib.util.spec_from_file_location("rustfs_restore", ROOT / "automation/rustfs-backup/restore-bucket.py")
RESTORE_MODULE = importlib.util.module_from_spec(RESTORE_SPEC)
assert RESTORE_SPEC.loader
RESTORE_SPEC.loader.exec_module(RESTORE_MODULE)


class RustFSManifestTests(unittest.TestCase):
    def test_restore_helper_resolves_source_layout(self):
        self.assertTrue((RESTORE_MODULE.SCRIPT_DIR / "common.py").is_file())

    def test_bucket_manifest_keeps_versions_and_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            metadata = {
                "bucket": "whiteboard",
                "objects": [{"Key": "a.txt", "VersionId": "v1", "Size": 3}],
                "files": [{"path": "a.txt", "size": 3, "sha256": "abc"}],
            }
            (root / "manifest.json").write_text(json.dumps(metadata))
            loaded = json.loads((root / "manifest.json").read_text())
            self.assertEqual(loaded["objects"][0]["VersionId"], "v1")
            self.assertEqual(loaded["files"][0]["sha256"], "abc")

    def test_restore_sync_uses_object_payload_only(self):
        args = RESTORE_MODULE.restore_sync_args("whiteboard", "whiteboard-restore")
        self.assertEqual(args[2], "/restore/rustfs/whiteboard/objects")
        self.assertNotIn("--exclude", args)

    def test_payload_uses_a_namespace_separate_from_backup_metadata(self):
        self.assertEqual(MODULE.payload_prefix("whiteboard"), "rustfs/whiteboard/objects")
        args = RESTORE_MODULE.restore_sync_args("whiteboard", "whiteboard-restore")
        self.assertIn("/restore/rustfs/whiteboard/objects", args)


if __name__ == "__main__":
    unittest.main()
