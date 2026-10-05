#!/usr/bin/env python3
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("coverage_manifest", ROOT / "automation/gitlab-backup/coverage-manifest.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class GitLabContractTests(unittest.TestCase):
    def test_manifest_records_registry_and_redis_boundary(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            native = root / "native.tar"
            config = root / "config.tar"
            registry = root / "registry.tar.gz"
            for path in (native, config, registry):
                path.write_bytes(b"artifact")
            output = root / "manifest.json"
            old_argv = sys.argv
            try:
                sys.argv = [
                    "coverage-manifest", "--output", str(output), "--version", "18.11.11",
                    "--native", str(native), "--config", str(config), "--registry", str(registry),
                    "--postgres-server-version", "16.14", "--pg-dump-version", "17.10",
                ]
                MODULE.main()
            finally:
                sys.argv = old_argv
            manifest = json.loads(output.read_text())
            self.assertEqual(manifest["gitlab_version"], "18.11.11")
            self.assertEqual(manifest["coverage"]["redis"], "excluded; cache, sessions, and Sidekiq queues rebuild")
            self.assertEqual({item["kind"] for item in manifest["files"]}, {"native_gitlab", "config_and_secrets", "local_registry"})
            self.assertEqual(manifest["postgresql"]["server_version"], "16.14")
            self.assertEqual(manifest["postgresql"]["dump_client_version"], "17.10")


if __name__ == "__main__":
    unittest.main()
