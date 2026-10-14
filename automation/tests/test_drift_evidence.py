import datetime as dt
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class DriftEvidenceTest(unittest.TestCase):
    def run_report(self, changes):
        evidence = {
            "mode": "observed", "status": "ok", "complete": True,
            "observed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "hosts": ["pi5"], "services": [], "routes": [],
        }
        evidence.update(changes)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "active.yaml").write_text('hosts: [{id: pi5}]\nservices: []\nroutes: []\n')
            (root / "observed.json").write_text(json.dumps(evidence))
            result = subprocess.run([
                sys.executable, str(ROOT / "automation/scripts/report-drift.py"),
                "--active", str(root / "active.yaml"),
                "--observed", str(root / "observed.json"),
            ], capture_output=True, text=True)
        return result.returncode, json.loads(result.stdout)

    def test_matching_inventory(self):
        code, report = self.run_report({})
        self.assertEqual(code, 0)
        self.assertEqual(report["scope"], "inventory_ids_only")

    def test_actual_drift(self):
        code, report = self.run_report({"hosts": []})
        self.assertEqual(code, 1)
        self.assertEqual(report["status"], "drift")

    def test_unverified_evidence_rejected(self):
        cases = [
            {"mode": "declarative"}, {"status": "failed"},
            {"complete": False}, {"complete": "true"},
            {"observed_at": "2000-01-01T00:00:00+00:00"},
            {"observed_at": "2999-01-01T00:00:00+00:00"},
            {"observed_at": "2026-10-14T12:00:00"},
            {"observed_at": None}, {"hosts": "pi5"},
            {"hosts": ["pi5", "pi5"]}, {"services": None},
        ]
        for changes in cases:
            with self.subTest(changes=changes):
                code, report = self.run_report(changes)
                self.assertEqual(code, 2)
                self.assertEqual(report["status"], "not_verified")


if __name__ == "__main__":
    unittest.main()
