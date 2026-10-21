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
                export.aws_command(
                    "http://rustfs:9000",
                    root / "credentials",
                    ["s3", "sync", "s3://bucket", "/export/objects"],
                    network="homelab-net",
                    image="amazon/aws-cli:2.17.60",
                    mount_root=root,
                )
            argv = run.call_args.args[0]
            self.assertIn("--user", argv)
            self.assertEqual(argv[argv.index("--user") + 1], f"{os.getuid()}:{os.getgid()}")
            self.assertIn("HOME=/tmp", argv)
            self.assertTrue(run.call_args.kwargs["check"])

    def test_network_transport_requires_all_runtime_inputs(self):
        inventory = {"rustfs": {"endpoint": "http://rustfs:9000"}}
        with patch.dict(os.environ, {"BACKUP_RUSTFS_TRANSPORT": "network"}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "BACKUP_RUSTFS_ENDPOINT"):
                export.transport_config(inventory)

    def test_network_transport_does_not_use_inventory_endpoint(self):
        inventory = {"rustfs": {"endpoint": "http://rustfs:9000"}}
        values = {
            "BACKUP_RUSTFS_TRANSPORT": "network",
            "BACKUP_RUSTFS_ENDPOINT": "http://tasks.rustfs:9000",
            "BACKUP_RUSTFS_NETWORK": "s3-net",
            "BACKUP_RUSTFS_CLIENT_IMAGE": "amazon/aws-cli:2.17.60@sha256:example",
        }
        with patch.dict(os.environ, values, clear=True):
            self.assertEqual(
                export.transport_config(inventory),
                ("http://tasks.rustfs:9000", "s3-net", "amazon/aws-cli:2.17.60@sha256:example"),
            )


if __name__ == "__main__":
    unittest.main()
