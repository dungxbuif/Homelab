#!/usr/bin/env python3
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("validate_inventory", ROOT / "backup/scripts/validate_inventory.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class InventoryTests(unittest.TestCase):
    def test_current_inventory_is_valid(self):
        inventory = json.loads((ROOT / "backup/inventory.yaml").read_text())
        policies = json.loads((ROOT / "backup/policies.yaml").read_text())
        self.assertEqual(MODULE.validate(inventory, policies), [])

    def test_duplicate_database_is_rejected(self):
        inventory = json.loads((ROOT / "backup/inventory.yaml").read_text())
        inventory["postgresql"]["databases"].append(inventory["postgresql"]["databases"][0])
        errors = MODULE.validate(inventory, json.loads((ROOT / "backup/policies.yaml").read_text()))
        self.assertTrue(any("duplicate postgresql" in error for error in errors))

    def test_invalid_bucket_is_rejected(self):
        inventory = json.loads((ROOT / "backup/inventory.yaml").read_text())
        inventory["rustfs"]["buckets"][0]["name"] = "../escape"
        errors = MODULE.validate(inventory, json.loads((ROOT / "backup/policies.yaml").read_text()))
        self.assertTrue(any("invalid bucket" in error for error in errors))

    def test_additional_instance_schema_is_enforced(self):
        policies = json.loads((ROOT / "backup/policies.yaml").read_text())
        valid = {"id": "relayhub", "host": "pi5", "container": "relayhub-pg",
                 "admin_user": "relayhub", "databases": [
                     {"name": "relayhub", "application": "relayhub", "lifecycle": "active"}]}
        for changes, rejected in [({}, False), ({"host": "vm100"}, False),
                                  ({"databases": []}, True), ({"id": "../bad"}, True),
                                  ({"container": "postgres"}, True),
                                  ({"databases": [{"name": "bad"}]}, True)]:
            with self.subTest(changes=changes):
                inventory = json.loads((ROOT / "backup/inventory.yaml").read_text())
                inventory["postgresql_instances"] = [{**valid, **changes}]
                self.assertEqual(bool(MODULE.validate(inventory, policies)), rejected)
        inventory["postgresql_instances"] = [valid, valid]
        self.assertTrue(MODULE.validate(inventory, policies))


if __name__ == "__main__":
    unittest.main()
