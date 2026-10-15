#!/usr/bin/env python3
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "automation/scripts/check-secrets.sh"


class SecretScanTest(unittest.TestCase):
    def scan(self, content=None, initialize=True, filename="settings.txt"):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            if initialize:
                subprocess.run(["git", "init", "-q", directory], check=True)
                (root / filename).write_text(content or "public setting\n")
                subprocess.run(["git", "-C", directory, "add", "."], check=True)
            return subprocess.run(["bash", str(SCRIPT), directory], capture_output=True, text=True)

    def test_clean_tracked_files_pass(self):
        self.assertEqual(self.scan().returncode, 0)

    def test_secret_fails_without_echoing_value(self):
        secret = "glpat-" + "a" * 24
        result = self.scan(secret)
        self.assertEqual(result.returncode, 1)
        self.assertNotIn(secret, result.stdout + result.stderr)
        self.assertIn("settings.txt", result.stdout + result.stderr)

    def test_invalid_repository_fails_closed(self):
        self.assertGreater(self.scan(initialize=False).returncode, 1)

    def test_markdown_secrets_are_not_excluded(self):
        secret = "github_pat_" + "a" * 30
        result = self.scan(secret, filename="RUNBOOK.md")
        self.assertEqual(result.returncode, 1)
        self.assertIn("RUNBOOK.md", result.stdout)
        self.assertNotIn(secret, result.stdout + result.stderr)

    def test_git_execution_failure_is_not_success(self):
        with tempfile.TemporaryDirectory() as directory:
            fake_git = Path(directory) / "git"
            fake_git.write_text("#!/bin/sh\nexit 128\n")
            fake_git.chmod(0o700)
            result = subprocess.run(
                ["bash", str(SCRIPT), directory],
                env={**os.environ, "PATH": directory + os.pathsep + os.environ["PATH"]},
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 128)


if __name__ == "__main__":
    unittest.main()
