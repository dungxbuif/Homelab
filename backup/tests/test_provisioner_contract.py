#!/usr/bin/env python3
import importlib.util
import json
import unittest
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "provisioner", ROOT / "backup/scripts/provisioner.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class ProvisionerContractTests(unittest.TestCase):
    def test_catalog_conflict_is_rejected_before_native_operations(self):
        normalized = {'engine': 'postgresql', 'name': 'example', 'owner_role': 'new_owner',
                      'secret_ref': 'swarm:example-db'}
        with patch.object(MODULE, 'validate_request', return_value=([], normalized)), \
             patch.object(MODULE, 'register_resource', create=True, side_effect=ValueError('catalog conflict')), \
             patch.object(MODULE, '_secret_exists', side_effect=AssertionError('native operation reached')) as native:
            with self.assertRaises(MODULE.ProvisioningError):
                MODULE.provision_postgresql({}, {'postgresql': {'container': 'pg', 'admin_user': 'admin'}}, {})
            native.assert_not_called()

    def test_postgres_partial_failure_preserves_generated_secret(self):
        request = {'_inventory_path': 'unused', '_policies_path': 'unused'}
        normalized = {'name': 'example', 'owner_role': 'example_app', 'secret_ref': 'swarm:example-db'}
        with patch.object(MODULE, '_validate', return_value=normalized), \
             patch.object(MODULE, '_secret_exists', return_value=False), \
             patch.object(MODULE, '_psql_scalar', return_value=''), \
             patch.object(MODULE, '_create_secret'), \
             patch.object(MODULE, '_remove_secret') as remove, \
             patch.object(MODULE, '_psql_script', side_effect=MODULE.ProvisioningError('partial SQL failure')):
            with self.assertRaises(MODULE.ProvisioningError):
                MODULE.provision_postgresql(request, {'postgresql': {'container': 'pg', 'admin_user': 'admin'}}, {})
            remove.assert_not_called()

    def test_couch_partial_failure_preserves_generated_secret(self):
        normalized = {'name': 'example', 'owner_identity': 'example_app',
                      'secret_ref': 'swarm:example-db', 'application': 'example'}
        with patch.object(MODULE, '_validate', return_value=normalized), \
             patch.object(MODULE, '_secret_exists', return_value=False), \
             patch.object(MODULE, '_create_secret'), \
             patch.object(MODULE, '_remove_secret') as remove, \
             patch.object(MODULE, '_couch_status', side_effect=['201', '404', '201', '500']):
            with self.assertRaises(MODULE.ProvisioningError):
                MODULE.provision_couchdb({}, {'couchdb': {'container': 'couch'}}, {})
            remove.assert_not_called()

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
