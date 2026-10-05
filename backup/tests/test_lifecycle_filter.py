#!/usr/bin/env python3
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("common", ROOT / "backup/scripts/common.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class LifecycleFilterTests(unittest.TestCase):
    def test_retired_entries_are_excluded_and_reported(self):
        selected, retired = MODULE.select_backup_entries([
            {"name": "active_db", "lifecycle": "active"},
            {"name": "old_db", "lifecycle": "retired"},
            {"name": "system_db", "lifecycle": "system"},
        ])
        self.assertEqual([entry["name"] for entry in selected], ["active_db", "system_db"])
        self.assertEqual(retired, ["old_db"])

    def test_postgres_adapter_does_not_dump_retired_databases(self):
        spec = importlib.util.spec_from_file_location("backup_postgres", ROOT / "backup/scripts/backup-postgres.py")
        module = importlib.util.module_from_spec(spec)
        assert spec.loader
        spec.loader.exec_module(module)

        def fake_docker_exec(_container, command, *, input_bytes=None):
            if command[0] == "pg_dumpall":
                return b"globals" * 16
            if command[0] == "pg_dump":
                return b"dump" * 64
            if command[0] == "pg_restore":
                return b"LIST;\n"
            raise AssertionError(command)

        inventory = {
            "postgresql": {
                "container": "postgres",
                "admin_user": "admin",
                "databases": [
                    {"name": "active_db", "application": "app", "lifecycle": "active"},
                    {"name": "old_db", "application": "old", "lifecycle": "retired"},
                ],
            }
        }
        with tempfile.TemporaryDirectory() as directory, patch.object(module, "docker_exec", side_effect=fake_docker_exec):
            manifest = module.create_backup(inventory, Path(directory))
        self.assertEqual([entry["name"] for entry in manifest["databases"]], ["active_db"])
        self.assertEqual(manifest["excluded_retired"], ["old_db"])


if __name__ == "__main__":
    unittest.main()
