#!/usr/bin/env python3
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "provisioner", ROOT / "backup/scripts/provisioner.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class ProvisionerContractTests(unittest.TestCase):
    def test_secret_ref_must_be_a_swarm_secret(self):
        self.assertEqual(MODULE.swarm_secret_name("swarm:notes-db"), "notes-db")
        with self.assertRaises(MODULE.ProvisioningError):
            MODULE.swarm_secret_name("file:/tmp/password")

    def test_postgres_sql_is_least_privilege_and_does_not_embed_admin_password(self):
        sql = MODULE.postgres_setup_sql(
            database="notes_staging",
            owner_role="notes_app",
            password="generated-secret-value",
            create_role=True,
            create_database=True,
        )
        self.assertIn('CREATE ROLE "notes_app"', sql)
        self.assertIn('CREATE DATABASE "notes_staging"', sql)
        self.assertIn('REVOKE ALL ON DATABASE "notes_staging" FROM PUBLIC', sql)
        self.assertIn('GRANT CONNECT ON DATABASE "notes_staging" TO "notes_app"', sql)
        self.assertIn("NOCREATEDB", sql.upper())
        self.assertIn("NOCREATEROLE", sql.upper())
        self.assertIn("NOSUPERUSER", sql.upper())

    def test_couchdb_security_payload_has_only_requested_member(self):
        payload = MODULE.couchdb_security_payload("notes_app", "notes")
        self.assertEqual(payload["admins"], {"names": [], "roles": []})
        self.assertEqual(payload["members"], {"names": ["notes_app"], "roles": ["notes"]})
        self.assertNotIn("password", json.dumps(payload))

    def test_public_result_never_contains_generated_password(self):
        result = MODULE.public_result(
            engine="postgresql",
            name="notes_staging",
            secret_ref="swarm:notes-db",
            changed=True,
            generated_password="must-not-leak",
        )
        self.assertNotIn("must-not-leak", json.dumps(result))
        self.assertEqual(result["secret_ref"], "swarm:notes-db")


if __name__ == "__main__":
    unittest.main()
