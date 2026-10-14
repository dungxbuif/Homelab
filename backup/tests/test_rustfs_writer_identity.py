import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("rustfs_export", ROOT / "automation/rustfs-backup/export-buckets.py")
export = importlib.util.module_from_spec(spec)
spec.loader.exec_module(export)


class RustFSWriterIdentityTest(unittest.TestCase):
    def test_bind_mount_writer_uses_host_owner(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(export.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, b"", b"")) as run:
                export.aws_command("http://rustfs:9000", root / "credentials", ["s3", "sync", "s3://bucket", "/export/objects"], mount_root=root)
            argv = run.call_args.args[0]
            self.assertIn("--user", argv)
            self.assertEqual(argv[argv.index("--user") + 1], f"{os.getuid()}:{os.getgid()}")
            self.assertIn("HOME=/tmp", argv)
            self.assertTrue(run.call_args.kwargs["check"])


if __name__ == "__main__":
    unittest.main()
