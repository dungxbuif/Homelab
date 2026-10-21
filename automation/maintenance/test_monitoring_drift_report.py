from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


class MonitoringDriftReportContractTest(unittest.TestCase):
    def test_wrapper_uses_existing_gate_and_notification_helper(self):
        source = (ROOT / "automation/maintenance/run-monitoring-drift-report.sh").read_text()
        self.assertIn("audit-monitoring-targets.py", source)
        self.assertIn("notify-mezon.sh", source)
        self.assertIn("--kind monitoring-drift", source)
        self.assertNotIn("https://webhook", source)

    def test_unit_uses_vm100_secret_and_lan_metrics(self):
        service = (ROOT / "automation/maintenance/systemd/homelab-monitoring-drift.service").read_text()
        timer = (ROOT / "automation/maintenance/systemd/homelab-monitoring-drift.timer").read_text()
        self.assertIn("VICTORIAMETRICS_URL=http://10.10.0.5:8428", service)
        self.assertIn("MEZON_WEBHOOK_URL_FILE=/etc/homelab-backup/secrets/mezon-webhook", service)
        self.assertIn("OnCalendar=*-*-* 11:30:00 Asia/Ho_Chi_Minh", timer)


if __name__ == "__main__":
    unittest.main()
