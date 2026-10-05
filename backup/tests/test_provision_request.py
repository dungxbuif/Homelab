#!/usr/bin/env python3
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("validate_provision_request", ROOT / "backup/scripts/validate_provision_request.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class ProvisionRequestTests(unittest.TestCase):
    def setUp(self):
        self.inventory = json.loads((ROOT / "backup/inventory.yaml").read_text())
        self.policies = json.loads((ROOT / "backup/policies.yaml").read_text())

    def test_valid_postgresql_request_requires_only_a_secret_reference(self):
        request = {
            "engine": "postgresql",
            "name": "notes_staging",
            "application": "notes",
            "environment": "staging",
            "owner_role": "notes_app",
            "policy_id": "db-default",
            "secret_ref": "swarm:notes-db",
        }
        errors, normalized = MODULE.validate_request(request, self.inventory, self.policies)
        self.assertEqual(errors, [])
        self.assertEqual(normalized["owner_role"], "notes_app")
        self.assertNotIn("password", normalized)

    def test_duplicate_and_system_database_are_rejected(self):
        request = {
            "engine": "postgresql",
            "name": "postgres",
            "application": "demo",
            "environment": "prod",
            "owner_role": "demo_app",
            "policy_id": "db-default",
            "secret_ref": "swarm:demo-db",
        }
        errors, _ = MODULE.validate_request(request, self.inventory, self.policies)
        self.assertTrue(any("reserved database" in error for error in errors))
        request["name"] = "bds_prod"
        errors, _ = MODULE.validate_request(request, self.inventory, self.policies)
        self.assertTrue(any("already exists" in error for error in errors))

    def test_unsafe_request_and_inline_password_are_rejected(self):
        request = {
            "engine": "postgresql",
            "name": "demo;drop",
            "application": "demo",
            "environment": "staging",
            "owner_role": "demo_app",
            "policy_id": "missing-policy",
            "secret_ref": "swarm:demo-db",
            "password": "must-not-be-accepted",
        }
        errors, _ = MODULE.validate_request(request, self.inventory, self.policies)
        self.assertTrue(any("inline password" in error for error in errors))
        self.assertTrue(any("invalid database" in error for error in errors))
        self.assertTrue(any("unknown policy" in error for error in errors))

    def test_couchdb_system_namespace_is_rejected(self):
        request = {
            "engine": "couchdb",
            "name": "_users",
            "application": "demo",
            "environment": "staging",
            "owner_identity": "demo_sync",
            "policy_id": "db-default",
            "secret_ref": "swarm:demo-couchdb",
        }
        errors, _ = MODULE.validate_request(request, self.inventory, self.policies)
        self.assertTrue(any("system CouchDB" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
