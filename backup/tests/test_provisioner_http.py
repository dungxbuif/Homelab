#!/usr/bin/env python3
import importlib.util
import inspect
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "provisioner_server", ROOT / "automation/provisioner/server.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class ProvisionerHttpTests(unittest.TestCase):
    def test_bearer_authorization_is_exact_and_case_sensitive(self):
        self.assertTrue(MODULE.authorized("Bearer abc", "abc"))
        self.assertFalse(MODULE.authorized("Bearer wrong", "abc"))
        self.assertFalse(MODULE.authorized("Basic abc", "abc"))
        self.assertFalse(MODULE.authorized(None, "abc"))

    def test_payload_rejects_oversized_or_non_object_requests(self):
        payload = MODULE.parse_payload(json.dumps({"engine": "postgresql"}).encode(), 4096)
        self.assertEqual(payload["engine"], "postgresql")
        with self.assertRaises(MODULE.RequestError):
            MODULE.parse_payload(b"[]", 4096)
        with self.assertRaises(MODULE.RequestError):
            MODULE.parse_payload(b"{}", 1)

    def test_handler_keeps_provision_function_unbound(self):
        self.assertIsInstance(inspect.getattr_static(MODULE.ProvisionerHandler, "provision"), staticmethod)


if __name__ == "__main__":
    unittest.main()
