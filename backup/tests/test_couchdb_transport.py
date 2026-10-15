#!/usr/bin/env python3
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("backup_couchdb", ROOT / "backup/scripts/backup-couchdb.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class CouchDBTransportTests(unittest.TestCase):
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
