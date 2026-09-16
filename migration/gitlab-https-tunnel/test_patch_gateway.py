import hashlib
import importlib
import importlib.util
import tempfile
import unittest
from pathlib import Path


BASE = b'''tcp:
  routers:
    rathole-passthrough:
      rule: "HostSNI(`n8n.dungxbuif.com`) || HostSNI(`gitlab.dungxbuif.com`) || HostSNI(`money.dungxbuif.com`)"
      entryPoints: [websecure]
      service: rathole-svc
  services:
    rathole-svc:
      loadBalancer:
        servers:
          - address: "rathole-server:443"
'''


class GatewayPatchTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec("patch_gateway"), "patch_gateway module missing")
        self.gateway = importlib.import_module("patch_gateway")

    def test_removes_only_gitlab_term(self):
        patched = self.gateway.patch_bytes(BASE)
        self.assertEqual(
            patched,
            BASE.replace(b" || HostSNI(`gitlab.dungxbuif.com`)", b""),
        )
        self.assertIn(b"HostSNI(`n8n.dungxbuif.com`)", patched)
        self.assertIn(b"HostSNI(`money.dungxbuif.com`)", patched)

    def test_rejects_missing_or_duplicate_gitlab(self):
        with self.assertRaises(ValueError):
            self.gateway.patch_bytes(BASE.replace(b" || HostSNI(`gitlab.dungxbuif.com`)", b""))
        with self.assertRaises(ValueError):
            self.gateway.patch_bytes(BASE.replace(
                b"HostSNI(`gitlab.dungxbuif.com`)",
                b"HostSNI(`gitlab.dungxbuif.com`) || HostSNI(`gitlab.dungxbuif.com`)",
            ))

    def test_apply_and_restore_keep_inode(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dynamic.yml"
            path.write_bytes(BASE)
            original_inode = path.stat().st_ino
            backup = self.gateway.apply_file(path, hashlib.sha256(BASE).hexdigest())
            self.assertTrue(backup.exists())
            self.assertEqual(backup.read_bytes(), BASE)
            self.assertEqual(path.stat().st_ino, original_inode)
            self.assertNotIn(b"HostSNI(`gitlab.dungxbuif.com`)", path.read_bytes())
            self.gateway.restore_file(path, backup)
            self.assertEqual(path.read_bytes(), BASE)
            self.assertEqual(path.stat().st_ino, original_inode)

    def test_hash_guard_leaves_file_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dynamic.yml"
            path.write_bytes(BASE)
            with self.assertRaises(ValueError):
                self.gateway.apply_file(path, "0" * 64)
            self.assertEqual(path.read_bytes(), BASE)
            self.assertEqual(list(Path(directory).glob("*.bak-*")), [])


if __name__ == "__main__":
    unittest.main()
