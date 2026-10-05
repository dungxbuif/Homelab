#!/usr/bin/env python3
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("health_report", ROOT / "backup/scripts/health-report.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class HealthReportTests(unittest.TestCase):
    def test_report_selects_complete_runs_and_restore_timestamp(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run = root / "db-20261005-0100"
            run.mkdir()
            (run / "COMPLETE").write_text("db-20261005-0100\n")
            (run / "manifest.json").write_text(json.dumps({
                "kind": "databases",
                "status": "complete",
                "run_id": "db-20261005-0100",
                "coverage": {"postgresql": [{"name": "bds_prod"}]},
            }))
            (run / "remote").mkdir()
            (run / "remote" / "snapshot-id").write_text("snap-db\n")
            (run / "restore-report-postgresql-bds.json").write_text("{}")
            report = MODULE.build_report(root)
            self.assertEqual(report["classes"]["databases"]["run_id"], "db-20261005-0100")
            self.assertEqual(report["classes"]["databases"]["snapshot_id"], "snap-db")
            self.assertIn("restore_test_latest", report["classes"]["databases"])
            encoded = json.dumps(report)
            self.assertNotIn("password", encoded.lower())


if __name__ == "__main__":
    unittest.main()
