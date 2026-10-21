import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "automation/maintenance/vps/external-heartbeat.py"
SPEC = importlib.util.spec_from_file_location("external_heartbeat", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ExternalHeartbeatContractTest(unittest.TestCase):
    def test_defaults_are_public_https_routes(self):
        self.assertTrue(MODULE.DEFAULT_URLS)
        self.assertTrue(all(url.startswith("https://") for url in MODULE.DEFAULT_URLS))

    def test_state_change_notifies_only_on_transition(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "state"
            webhook = Path(tmp) / "webhook"
            webhook.write_text("https://example.invalid/webhook\n")
            old_state = os.environ.get("HEARTBEAT_STATE_FILE")
            old_webhook = os.environ.get("MEZON_WEBHOOK_FILE")
            try:
                os.environ["HEARTBEAT_STATE_FILE"] = str(state)
                os.environ["MEZON_WEBHOOK_FILE"] = str(webhook)
                with patch.object(MODULE, "probe", return_value=(True, "HTTP 200")), patch.object(MODULE, "notify") as notify:
                    self.assertEqual(MODULE.main(), 0)
                    self.assertEqual(MODULE.main(), 0)
                notify.assert_called_once()
                self.assertEqual(state.read_text(), "healthy\n")
            finally:
                if old_state is None:
                    os.environ.pop("HEARTBEAT_STATE_FILE", None)
                else:
                    os.environ["HEARTBEAT_STATE_FILE"] = old_state
                if old_webhook is None:
                    os.environ.pop("MEZON_WEBHOOK_FILE", None)
                else:
                    os.environ["MEZON_WEBHOOK_FILE"] = old_webhook

    def test_no_webhook_is_embedded(self):
        source = SCRIPT.read_text()
        self.assertIn("MEZON_WEBHOOK_FILE", source)
        self.assertNotIn("webhook.mezon.ai/webhooks/", source)


if __name__ == "__main__":
    unittest.main()
