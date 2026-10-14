from pathlib import Path
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[1]


class ControlNetworkTest(unittest.TestCase):
    def test_ui_uses_isolated_network_and_single_writer_rollout(self):
        service = yaml.safe_load((ROOT / "stack.yml").read_text())["services"]["semaphore"]
        self.assertEqual(service["networks"], ["homelab-control-net"])
        self.assertEqual(service["dns"], ["10.10.0.5"])
        self.assertEqual(service["deploy"]["update_config"]["order"], "stop-first")
        self.assertIn("/ssd-data/infra/semaphore/data:/var/lib/semaphore", service["volumes"])
        self.assertIn("homelab_provisioner_token", service["secrets"])


if __name__ == "__main__":
    unittest.main()
