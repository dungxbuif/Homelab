#!/usr/bin/env python3
import importlib.util
import os
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("sync_obsidian_vault", ROOT / "goclaw/scripts/sync_obsidian_vault.py")
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


class SyncVaultTest(unittest.TestCase):
    def test_remote_path_is_shell_quoted(self):
        args = Namespace(vault_root=Path("."), remote="u@h", remote_path="/data/x; touch /tmp/pwn", dry_run=True, exclude=[])
        dest = mod.build_rsync_cmd(args)[-1]
        self.assertEqual(dest, "u@h:'/data/x; touch /tmp/pwn'")

    def test_token_from_file_and_env(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "t"
            f.write_text("file-value\n")
            old = os.environ.pop("GOCLAW_TOKEN", None)
            try:
                self.assertEqual(mod.fetch_token(f), "file-value")
                os.environ["GOCLAW_TOKEN"] = "env-value"
                self.assertEqual(mod.fetch_token(None), "env-value")
                del os.environ["GOCLAW_TOKEN"]
                with self.assertRaises(RuntimeError):
                    mod.fetch_token(None)
            finally:
                if old is not None:
                    os.environ["GOCLAW_TOKEN"] = old

    def test_no_insecure_tls_or_ssh_token_fetch(self):
        src = (ROOT / "goclaw/scripts/sync_obsidian_vault.py").read_text()
        self.assertNotIn("_create_unverified_context", src)
        self.assertNotIn("--insecure", src)
        self.assertNotIn("awk", src)


if __name__ == "__main__":
    unittest.main()
