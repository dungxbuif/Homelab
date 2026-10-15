import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/run-database-backup.py"
SPEC = importlib.util.spec_from_file_location("database_runner", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class DatabaseInstancesTest(unittest.TestCase):
    def inventory(self):
        return {
            "postgresql": {"host": "pi5", "container": "postgres"},
            "couchdb": {},
            "postgresql_instances": [{
                "id": "relayhub", "host": "pi5", "container": "relayhub-pg",
                "admin_user": "relayhub", "databases": [
                    {"name": "relayhub", "application": "relayhub", "lifecycle": "active"}
                ],
            }],
        }

    def execute(self, root, inventory, postgres):
        path = root / "inventory.json"
        path.write_text(json.dumps(inventory))
        couch = Mock()
        couch.create_backup.return_value = {"databases": []}
        with patch.object(MODULE, "load_adapter", side_effect=[postgres, couch]):
            return MODULE.run(path, root / "runs", "test-run")

    def test_additional_instance_has_separate_path_and_coverage(self):
        pg = Mock()
        pg.create_backup.return_value = {"databases": []}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run = self.execute(root, self.inventory(), pg)
            calls = pg.create_backup.call_args_list
            self.assertEqual(len(calls), 2)
            self.assertEqual(calls[1].args[0]["postgresql"]["container"], "relayhub-pg")
            self.assertEqual(calls[1].args[1], root / "runs/.test-run.incomplete/instances/relayhub")
            manifest = json.loads((run / "manifest.json").read_text())
            self.assertEqual(manifest["coverage"]["postgresql_instances"]["relayhub"]["run_dir"], "instances/relayhub")

    def test_legacy_inventory_preserves_manifest(self):
        pg = Mock()
        pg.create_backup.return_value = {"databases": []}
        inv = self.inventory()
        del inv["postgresql_instances"]
        with tempfile.TemporaryDirectory() as tmp:
            run = self.execute(Path(tmp), inv, pg)
            self.assertEqual(pg.create_backup.call_count, 1)
            self.assertNotIn("postgresql_instances", json.loads((run / "manifest.json").read_text())["coverage"])

    def test_failed_instance_never_publishes_complete(self):
        pg = Mock()
        pg.create_backup.side_effect = [{}, RuntimeError("unavailable")]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaisesRegex(RuntimeError, "unavailable"):
                self.execute(root, self.inventory(), pg)
            self.assertFalse((root / "runs/test-run").exists())
            self.assertFalse((root / "runs/.test-run.incomplete/COMPLETE").exists())

    def test_invalid_instances_rejected_before_export(self):
        for mutation in [
            lambda x: x[0].update(id="../escape"),
            lambda x: x[0].update(host="vm100"),
            lambda x: x.append(dict(x[0])),
            lambda x: x[0].update(container="postgres"),
            lambda x: x[0].pop("admin_user"),
            lambda x: x[0].update(container="--privileged"),
            lambda x: x[0].update(databases=[{"name": "x"}]),
            lambda x: x[0].update(databases=[]),
        ]:
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as tmp:
                inv = self.inventory()
                mutation(inv["postgresql_instances"])
                pg = Mock()
                pg.create_backup.return_value = {}
                with self.assertRaises(ValueError):
                    self.execute(Path(tmp), inv, pg)
                pg.create_backup.assert_not_called()

    def test_native_adapter_files_are_separated_and_checksummed(self):
        pg = MODULE.load_adapter("backup-postgres.py", "postgres_instance_fixture")
        inv = self.inventory()
        entry = {"name": "postgres", "application": "system", "lifecycle": "system"}
        inv["postgresql"].update(admin_user="admin", databases=[entry])
        inv["postgresql_instances"][0]["databases"] = [entry]

        def native(container, command, **kwargs):
            if command[0] == "pg_dumpall":
                return b"-- globals fixture\n" * 4
            if command[0] == "pg_dump":
                return container.encode() * 128
            if command[0] == "pg_restore":
                return b"; native listing fixture\n"
            raise AssertionError(command)

        with tempfile.TemporaryDirectory() as tmp, patch.object(pg, "docker_exec", side_effect=native):
            run = self.execute(Path(tmp), inv, pg)
            primary = run / "postgresql/postgres.dump"
            additional = run / "instances/relayhub/postgresql/postgres.dump"
            self.assertNotEqual(primary.read_bytes(), additional.read_bytes())
            manifest = json.loads((run / "manifest.json").read_text())
            paths = {item["path"] for item in manifest["artifacts"]}
            self.assertIn("instances/relayhub/postgresql-adapter.json", paths)
            self.assertIn("instances/relayhub/postgresql/postgres.dump", paths)
            adapter = json.loads((run / "instances/relayhub/postgresql-adapter.json").read_text())
            self.assertTrue((run / "instances/relayhub" / adapter["databases"][0]["dump"]).is_file())


if __name__ == "__main__":
    unittest.main()
