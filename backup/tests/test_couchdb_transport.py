#!/usr/bin/env python3
import importlib.util
import json
import tempfile
import unittest
from unittest import mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("backup_couchdb", ROOT / "backup/scripts/backup-couchdb.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class CouchDBTransportTests(unittest.TestCase):
    def test_gzip_docs_round_trip_helper(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(
            MODULE.os.environ, {"BACKUP_COUCHDB_COMPRESSION": "gzip"}
        ):
            path = MODULE.docs_file_path(Path(tmp), "homelab")
            with MODULE.open_docs_file(path) as handle:
                handle.write('{"_id":"one"}\\n')
            self.assertTrue(path.name.endswith(".docs.ndjson.gz"))
            import gzip
            with gzip.open(path, "rt", encoding="utf-8") as handle:
                self.assertEqual(handle.read(), '{"_id":"one"}\\n')

    def test_create_backup_records_compressed_manifest_path(self):
        inventory = {
            "couchdb": {
                "container": "couchdb",
                "databases": [{"name": "homelab", "application": "lab", "lifecycle": "active"}],
            }
        }
        responses = iter(
            [
                {"db_name": "homelab", "doc_count": 1},
                {},
                {"rows": [{"id": "one", "doc": {"_id": "one"}}]},
                {"rows": []},
            ]
        )
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(
            MODULE.os.environ, {"BACKUP_COUCHDB_COMPRESSION": "gzip"}
        ), mock.patch.object(MODULE, "curl_db", side_effect=lambda *_args: json.dumps(next(responses)).encode()):
            manifest = MODULE.create_backup(inventory, Path(tmp))
        self.assertEqual(manifest["databases"][0]["doc_count"], 1)
        self.assertTrue(manifest["databases"][0]["docs"].endswith(".docs.ndjson.gz"))

    def test_requests_are_bounded_and_retry_transient_failures(self):
        captured = []

        def fake_docker_exec(container, command, *, input_bytes=None):
            captured.append((container, command))
            return b"{}"

        original = MODULE.docker_exec
        MODULE.docker_exec = fake_docker_exec
        try:
            MODULE.curl_db("couchdb", "obsidian_vault", "")
        finally:
            MODULE.docker_exec = original

        command = captured[0][1]
        script = command[-1]
        self.assertIn("--connect-timeout 15", script)
        self.assertIn("--max-time 900", script)
        self.assertIn("--retry 5", script)
        self.assertIn("--retry-max-time 900", script)
        self.assertIn("--retry-connrefused", script)


if __name__ == "__main__":
    unittest.main()
