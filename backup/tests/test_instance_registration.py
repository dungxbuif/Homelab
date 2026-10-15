import importlib.util
import json
import multiprocessing
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("instance_registration", ROOT / "backup/scripts/register_resource.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class InstanceRegistrationTests(unittest.TestCase):
    def request(self):
        return {"id": "relayhub", "host": "pi5", "container": "relayhub-pg",
                "admin_user": "relayhub", "databases": [
                    {"name": "relayhub", "application": "relayhub", "lifecycle": "active"}]}

    def test_registration_preserves_catalog_metadata_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "inventory.yaml"
            original = json.loads((ROOT / "backup/inventory.yaml").read_text())
            path.write_text(json.dumps(original))
            path.chmod(0o640)
            stat = path.stat()
            result = MODULE.register_instance_file(path, self.request())
            self.assertTrue(result["changed"])
            updated = json.loads(path.read_text())
            self.assertEqual(updated.pop("postgresql_instances"), [self.request()])
            self.assertEqual(updated, original)
            self.assertEqual(path.stat().st_mode & 0o777, 0o640)
            self.assertEqual((path.stat().st_uid, path.stat().st_gid), (stat.st_uid, stat.st_gid))
            before = path.read_bytes()
            self.assertFalse(MODULE.register_instance_file(path, self.request())["changed"])
            self.assertEqual(path.read_bytes(), before)
            self.assertTrue((path.parent / ".inventory.yaml.lock").exists())

    def test_conflicts_and_secrets_never_modify_catalog(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "inventory.yaml"
            path.write_text((ROOT / "backup/inventory.yaml").read_text())
            MODULE.register_instance_file(path, self.request())
            before = path.read_bytes()
            for changed in [{"container": "other"}, {"password": "fixture"}, {"host": "vm100"},
                            {"databases": [{**self.request()["databases"][0], "password": "fixture"}]}]:
                with self.subTest(changed=changed), self.assertRaises(ValueError):
                    MODULE.register_instance_file(path, {**self.request(), **changed})
                self.assertEqual(path.read_bytes(), before)

    def test_instance_and_provisioner_writers_preserve_both_updates(self):
        context = multiprocessing.get_context("fork")
        provision = {"engine": "postgresql", "name": "concurrent_fixture",
                     "application": "fixture", "environment": "staging",
                     "owner_role": "fixture_owner", "policy_id": "db-default",
                     "secret_ref": "swarm:fixture"}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "inventory.yaml"
            path.write_text((ROOT / "backup/inventory.yaml").read_text())
            processes = [
                context.Process(target=MODULE.register_instance_file, args=(path, self.request())),
                context.Process(target=MODULE.register_file,
                                args=(path, provision, ROOT / "backup/policies.yaml")),
            ]
            try:
                for process in processes:
                    process.start()
                for process in processes:
                    process.join(timeout=5)
                    self.assertEqual(process.exitcode, 0)
            finally:
                for process in processes:
                    if process.is_alive():
                        process.terminate()
                        process.join()
            inventory = json.loads(path.read_text())
            self.assertEqual(inventory["postgresql_instances"], [self.request()])
            self.assertIn("concurrent_fixture", [x["name"] for x in inventory["postgresql"]["databases"]])


if __name__ == "__main__":
    unittest.main()
