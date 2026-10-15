#!/usr/bin/env python3
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run-instance-backup.py"
SPEC = importlib.util.spec_from_file_location("instance_runner", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class InstanceBackupTests(unittest.TestCase):
    def inventory(self):
        return {
            "postgresql": {"host": "pi5", "container": "postgres"},
            "postgresql_instances": [
                {
                    "id": "relayhub",
                    "host": "pi5",
                    "container": "relayhub-pg",
                    "admin_user": "relayhub",
                    "databases": [{"name": "relayhub", "application": "relayhub", "lifecycle": "active"}],
                },
                {
                    "id": "couchloom",
                    "host": "vm100",
                    "container": "couchloom-postgres",
                    "admin_user": "couchloom",
                    "databases": [{"name": "couchloom", "application": "couchloom", "lifecycle": "active"}],
                },
            ],
        }

    def test_exports_only_instances_on_requested_host(self):
        postgres = Mock()
        postgres.create_backup.return_value = {"databases": []}
        with tempfile.TemporaryDirectory() as tmp, patch.object(MODULE, "load_adapter", return_value=postgres):
            inventory_path = Path(tmp) / "inventory.json"
            inventory_path.write_text(json.dumps(self.inventory()))
            run = MODULE.run(inventory_path, Path(tmp) / "runs", "database-instances-run", "vm100")
            postgres.create_backup.assert_called_once()
            config, output = postgres.create_backup.call_args.args
            self.assertEqual(config["postgresql"]["container"], "couchloom-postgres")
            self.assertEqual(output.name, "couchloom")
            manifest = json.loads((run / "manifest.json").read_text())
            self.assertEqual(manifest["kind"], "database-instances")
            self.assertEqual(manifest["coverage"]["postgresql_instances"]["couchloom"]["host"], "vm100")
            self.assertEqual(run.stat().st_mode & 0o777, 0o700)
            self.assertEqual((run / "manifest.json").stat().st_mode & 0o777, 0o600)

    def test_missing_host_instance_fails_before_export(self):
        postgres = Mock()
        with tempfile.TemporaryDirectory() as tmp, patch.object(MODULE, "load_adapter", return_value=postgres):
            inventory_path = Path(tmp) / "inventory.json"
            inventory_path.write_text(json.dumps(self.inventory()))
            with self.assertRaisesRegex(ValueError, "no PostgreSQL instances configured for host"):
                MODULE.run(inventory_path, Path(tmp) / "runs", "database-instances-run", "vps")
        postgres.create_backup.assert_not_called()

    def test_failed_instance_does_not_publish_complete_run(self):
        postgres = Mock()
        postgres.create_backup.side_effect = RuntimeError("container unavailable")
        with tempfile.TemporaryDirectory() as tmp, patch.object(MODULE, "load_adapter", return_value=postgres):
            inventory_path = Path(tmp) / "inventory.json"
            inventory_path.write_text(json.dumps(self.inventory()))
            with self.assertRaisesRegex(RuntimeError, "container unavailable"):
                MODULE.run(inventory_path, Path(tmp) / "runs", "database-instances-run", "vm100")
            self.assertFalse((Path(tmp) / "runs/database-instances-run").exists())
            self.assertFalse((Path(tmp) / "runs/.database-instances-run.incomplete/COMPLETE").exists())


if __name__ == "__main__":
    unittest.main()
