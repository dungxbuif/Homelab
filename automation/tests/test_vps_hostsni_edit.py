import hashlib
import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).parents[2]
MODULE_PATH = ROOT / "automation/scripts/vps-hostsni-edit.py"
SPEC = importlib.util.spec_from_file_location("vps_hostsni_edit", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


BASE = b'''tcp:\n  routers:\n    rathole-passthrough:\n      rule: "HostSNI(`one.example`) || HostSNI(`remove.example`) || HostSNI(`three.example`)"\n'''


class VpsHostSniEditTests(unittest.TestCase):
    def test_proposal_changes_only_requested_term(self):
        proposed = MODULE.propose(BASE, "remove.example")
        self.assertNotIn(b"remove.example", proposed)
        self.assertIn(b"one.example", proposed)
        self.assertIn(b"three.example", proposed)

    def test_requires_exactly_one_term(self):
        with self.assertRaisesRegex(ValueError, "exactly one"):
            MODULE.propose(BASE.replace(b"remove.example", b"three.example"), "three.example")

    def test_apply_preserves_inode_and_creates_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dynamic.yml"
            path.write_bytes(BASE)
            inode = path.stat().st_ino
            with patch.object(MODULE, "validate_provider"):
                backup = MODULE.apply(path, MODULE.propose(BASE, "remove.example"))
            self.assertEqual(path.stat().st_ino, inode)
            self.assertEqual(backup.read_bytes(), BASE)
            self.assertNotIn(b"remove.example", path.read_bytes())

    def test_hash_mismatch_is_rejected_by_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dynamic.yml"
            static = Path(directory) / "traefik.yml"
            path.write_bytes(BASE)
            static.write_text("providers: {}\n")
            result = subprocess.run(
                [
                    sys.executable,
                    str(MODULE_PATH),
                    "--path",
                    str(path),
                    "--static-config",
                    str(static),
                    "--expect-sha256",
                    "0" * 64,
                    "--remove-host",
                    "remove.example",
                ],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("current VPS dynamic config hash differs", result.stderr)

    def test_restore_preserves_inode(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dynamic.yml"
            backup = Path(directory) / "dynamic.yml.bak"
            path.write_bytes(MODULE.propose(BASE, "remove.example"))
            backup.write_bytes(BASE)
            inode = path.stat().st_ino
            MODULE.restore(path, backup, None, "traefik:v3.6", 1)
            self.assertEqual(path.stat().st_ino, inode)
            self.assertEqual(path.read_bytes(), BASE)

    def test_timeout_output_accepts_bytes(self):
        process = type("Process", (), {})()

        class Expired(subprocess.TimeoutExpired):
            pass

        with patch.object(MODULE.subprocess, "Popen") as popen:
            popen.return_value.communicate.side_effect = [
                Expired(["docker"], 1, output=b"Starting provider *file.Provider\n"),
                ("Starting provider *file.Provider\n", None),
            ]
            popen.return_value.kill.return_value = None
            with tempfile.TemporaryDirectory() as directory:
                static = Path(directory) / "traefik.yml"
                static.write_text("providers: {}\n")
                MODULE.validate_provider(b"tcp: {}\n", static, "traefik:v3.6", 1)


if __name__ == "__main__":
    unittest.main()
