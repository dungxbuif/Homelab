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
                (root / filename).parent.mkdir(parents=True, exist_ok=True)
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

    def assert_flagged(self, content, filename, rule, secret):
        result = self.scan(content, filename=filename)
        out = result.stdout + result.stderr
        self.assertEqual(result.returncode, 1, out)
        self.assertIn(filename, out)
        self.assertIn(rule, out)
        self.assertNotIn(secret, out)

    def test_basic_auth_flag_in_docs(self):
        secret = "Zq" + "9xT" * 4
        self.assert_flagged(f"{'cu' + 'rl'} -s -u admin:{secret} https://x.example/api\n", "docs/notes.md", "basic-auth-flag", secret)

    def test_authorization_basic_header(self):
        secret = "YWRtaW46" + "QWJjMTIzNDU2"
        self.assert_flagged(f"Authorization: Basic {secret}\n", "monitoring/SKILL.md", "authorization-basic", secret)

    def test_k8s_secret_base64_data_block(self):
        secret = "c3VwZXJzZWNyZXR2YWx1ZQ=="
        manifest = f"apiVersion: v1\nkind: Secret\nmetadata:\n  name: x\ndata:\n  api-token: {secret}\n"
        self.assert_flagged(manifest, "deprecated/x/issuer.secret.yml", "k8s-secret-base64-data", secret)

    def test_rathole_default_token(self):
        secret = "Hunter2" + "Pass9"
        self.assert_flagged(f'[client]\ndefault_token = "{secret}"\n', "docs/archived/rathole.toml", "rathole-token", secret)

    def test_high_entropy_assignment(self):
        secret = "aB3dE5gH7jK9mN2p" + "Q4sT6vX8zC1fL0wR"
        self.assert_flagged(f"N8N_ENCRYPTION_KEY: {secret}\n", "deprecated/n8n.md", "high-entropy-token", secret)

    def test_placeholders_pass(self):
        content = (
            'curl -s -H "Authorization: Bearer $GRAFANA_TOKEN" https://x\n'
            'default_token = "REDACTED"\n'
            'token = "__TOKEN__"\n'
            "kind: Secret\ndata:\n  k: REDACTED\n"
        )
        result = self.scan(content, filename="docs/ok.md")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_no_secret_output_helper(self):
        helper = ROOT / "automation/tests/test_no-secret-output.sh"
        with tempfile.TemporaryDirectory() as directory:
            bad = Path(directory) / "bad.txt"
            bad.write_text("Authorization: Basic " + "QUJDREVGR0hJSg==" + "\n")
            result = subprocess.run(["bash", str(helper), str(bad)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertNotIn("QUJDREVGR0hJSg", result.stdout + result.stderr)
            good = Path(directory) / "good.txt"
            good.write_text("all green\n")
            self.assertEqual(subprocess.run(["bash", str(helper), str(good)]).returncode, 0)

    def test_repository_itself_is_clean(self):
        result = subprocess.run(["bash", str(SCRIPT), str(ROOT)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

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
