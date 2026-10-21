import os
import importlib
import unittest
from unittest.mock import patch


class ProxyContractTests(unittest.TestCase):
    def test_route_allows_only_backup_paths(self):
        with patch.dict(os.environ, {"COUCHDB_ALLOWED_DATABASES": "homelab,obsidian_vault,_users"}, clear=False):
            import server
            server = importlib.reload(server)
            self.assertEqual(server.route_path("/obsidian_vault"), "/obsidian_vault")
            self.assertEqual(server.route_path("/obsidian_vault/_security"), "/obsidian_vault/_security")
            self.assertIsNone(server.route_path("/obsidian_vault/_bulk_docs"))
            self.assertIsNone(server.route_path("/obsidian_vault/_all_docs?foo=bar"))

    def test_client_cidr_is_exact(self):
        with patch.dict(os.environ, {"ALLOWED_CLIENT_CIDRS": "10.10.0.31/32"}, clear=False):
            import server
            server = importlib.reload(server)
            self.assertTrue(server.valid_client("10.10.0.31"))
            self.assertFalse(server.valid_client("10.10.0.32"))


if __name__ == "__main__":
    unittest.main()
