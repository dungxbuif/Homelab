import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "automation/scripts/collect-runtime-evidence.py"


def artifact(host, name="homepage", service=None):
    row = {"id": "abc123", "name": name, "state": "running", "service": service,
           "project": None, "image": "example:latest", "networks": "edge-http-net",
           "ports": ""}
    probes = {name: {"output": ""} for name in {
        "kernel", "memory", "swap", "disk", "listeners", "containers",
        "container_inventory", "resource_limits", "networks", "swarm_services", "resources",
    }}
    probes["container_inventory"]["output"] = json.dumps(row) + "\n"
    now = datetime.now(timezone.utc).isoformat()
    report = {"schema_version": 1, "scope": "host_runtime_only",
              "collection_complete": True, "inventory_complete": False,
              "observed_at": now, "probes": probes}
    return {"schema_version": 1, "host": host, "task_id": 1, "template_id": 4,
            "observed_at": now, "scope": "host_runtime_only",
            "inventory_complete": False, "report": report}


class CollectorTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.artifacts = self.root / "artifacts"
        self.artifacts.mkdir(mode=0o700)
        self.policy = self.root / "active.yaml"
        self.policy.write_text(
            "hosts:\n  - id: pi5\n  - id: vm100\n"
            "services:\n  - id: homepage\n    host: vm100\n    runtime_container: homepage\n"
            "routes:\n  - id: homepage\n", encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def write_artifact(self, host, value=None):
        path = self.artifacts / f"{host}.json"
        path.write_text(json.dumps(value or artifact(host)), encoding="utf-8")
        os.chmod(path, 0o600)

    def run_cli(self):
        return subprocess.run([sys.executable, str(SCRIPT), "--active", str(self.policy),
                               "--artifacts-dir", str(self.artifacts)],
                              capture_output=True, text=True)

    def test_missing_scope_is_not_verified_without_echoing_secrets(self):
        result = self.run_cli()
        self.assertEqual(result.returncode, 2)
        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "not_verified")
        self.assertIn("missing_hosts", report["coverage"])
        self.assertEqual(result.stderr, "")

    def test_fresh_host_artifacts_map_only_exact_runtime_names(self):
        self.write_artifact("pi5", artifact("pi5", name="other"))
        self.write_artifact("vm100")
        result = self.run_cli()
        self.assertEqual(result.returncode, 2)
        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "not_verified")
        self.assertEqual(report["services"], ["homepage"])
        self.assertEqual(report["coverage"]["missing_routes"], ["homepage"])

    def test_artifact_must_be_private_and_regular(self):
        self.write_artifact("pi5")
        os.chmod(self.artifacts / "pi5.json", stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP)
        result = self.run_cli()
        self.assertEqual(result.returncode, 2)
        report = json.loads(result.stdout)
        self.assertTrue(any("mode 0600" in error for error in report["coverage"]["errors"]))

    def test_output_is_exclusive_and_private(self):
        output = self.artifacts / "combined.json"
        result = subprocess.run([sys.executable, str(SCRIPT), "--active", str(self.policy),
                                 "--artifacts-dir", str(self.artifacts), "--output", str(output)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o600)
        second = subprocess.run([sys.executable, str(SCRIPT), "--active", str(self.policy),
                                 "--artifacts-dir", str(self.artifacts), "--output", str(output)],
                                capture_output=True, text=True)
        self.assertEqual(second.returncode, 2)
        self.assertEqual(json.loads(second.stdout)["reason"], "private output could not be created")


if __name__ == "__main__":
    unittest.main()
