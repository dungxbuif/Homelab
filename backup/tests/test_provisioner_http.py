#!/usr/bin/env python3
import importlib.util
import inspect
import json
import unittest
import threading
import urllib.request
import urllib.error
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "provisioner_server", ROOT / "automation/provisioner/server.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class ProvisionerHttpTests(unittest.TestCase):
    def test_busy_operation_is_retryable_conflict_without_secret_output(self):
        def busy(*args):
            raise MODULE.ProvisioningBusyError('another provisioning operation is in progress; retry later')

        class Handler(MODULE.ProvisionerHandler):
            token = 'fixture-token'
            provision = staticmethod(busy)

        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            request = urllib.request.Request(
                f'http://127.0.0.1:{server.server_port}/v1/provision', data=b'{}',
                headers={'Authorization': 'Bearer fixture-token', 'Content-Type': 'application/json'})
            with self.assertRaises(urllib.error.HTTPError) as raised:
                urllib.request.urlopen(request, timeout=3)
            with raised.exception as response:
                self.assertEqual(response.code, 409)
                body = response.read().decode()
                self.assertIn('retry later', body)
                self.assertNotIn('fixture-token', body)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)

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
