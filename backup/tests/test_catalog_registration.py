#!/usr/bin/env python3
import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load_module(filename: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "backup/scripts" / filename)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


VALIDATOR = load_module("validate_provision_request.py", "validate_provision_request")
CATALOG = load_module("register_resource.py", "register_resource")


class CatalogRegistrationTests(unittest.TestCase):
    def setUp(self):
        self.inventory = json.loads((ROOT / "backup/inventory.yaml").read_text())
        self.policies = json.loads((ROOT / "backup/policies.yaml").read_text())
        self.request = {
            "engine": "postgresql",
            "name": "notes_staging",
            "application": "notes",
            "environment": "staging",
            "owner_role": "notes_app",
            "policy_id": "db-default",
            "secret_ref": "swarm:notes-db",
        }

    def test_registration_adds_metadata_only_and_is_idempotent(self):
        updated, changed = CATALOG.register_resource(
            copy.deepcopy(self.inventory), self.request, self.policies
        )
        self.assertTrue(changed)
        entry = next(item for item in updated["postgresql"]["databases"] if item["name"] == "notes_staging")
        self.assertEqual(entry["lifecycle"], "active")
        self.assertEqual(entry["policy_id"], "db-default")
        self.assertEqual(entry["secret_ref"], "swarm:notes-db")
        self.assertNotIn('"password":', json.dumps(updated))

        repeated, repeated_changed = CATALOG.register_resource(updated, self.request, self.policies)
        self.assertFalse(repeated_changed)
        self.assertEqual(repeated, updated)

    def test_conflicting_existing_entry_is_rejected(self):
        inventory, _ = CATALOG.register_resource(copy.deepcopy(self.inventory), self.request, self.policies)
        conflict = dict(self.request, secret_ref="swarm:other-secret")
        with self.assertRaises(CATALOG.CatalogConflict):
            CATALOG.register_resource(inventory, conflict, self.policies)

    def test_file_update_is_atomic_and_does_not_write_password(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "inventory.yaml"
            path.write_text(json.dumps(self.inventory), encoding="utf-8")
            path.chmod(0o640)
            original = path.stat()
            result = CATALOG.register_file(path, self.request, ROOT / "backup/policies.yaml")
            self.assertTrue(result["changed"])
            payload = json.loads(path.read_text())
            self.assertNotIn('"password":', json.dumps(payload))
            self.assertTrue((path.parent / ".inventory.yaml.lock").exists())
            self.assertEqual(path.stat().st_mode & 0o777, 0o640)
            self.assertEqual((path.stat().st_uid, path.stat().st_gid), (original.st_uid, original.st_gid))


if __name__ == "__main__":
    unittest.main()
