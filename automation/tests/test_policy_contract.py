#!/usr/bin/env python3
import json
import subprocess
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]


class PolicyContractTest(unittest.TestCase):
    def test_verified_control_and_app_network_boundaries(self):
        active = yaml.safe_load((ROOT / "automation/policies/active-runtime.yaml").read_text())
        services = {item['id']: item for item in active['services']}
        expected = {
            'semaphore': {'homelab-control-net'},
            'semaphore-executor': {'homelab-control-net'},
            'provisioner': {'homelab-net', 'homelab-control-net'},
            'homepage': {'edge-http-net'},
            'couchloom': {'couchloom-internal', 'homelab-net'},
            'bds-app': {'bds-tunnel-net', 'homelab-net'},
            'bds-cloudflared': {'bds-tunnel-net'},
            'kubekosh': {'homelab-net'},
        }
        for name, networks in expected.items():
            self.assertEqual(set(services[name]['networks']), networks, name)
        self.assertFalse(active['inventory_complete'])

    def test_active_policy_excludes_kubernetes_and_retired_targets(self):
        active = yaml.safe_load((ROOT / "automation/policies/active-runtime.yaml").read_text())
        retired = yaml.safe_load((ROOT / "automation/policies/retired-runtime.yaml").read_text())
        active_ids = {item["id"] for key in ("hosts", "services", "routes") for item in active[key]}
        retired_ids = {item["id"] for key in ("hosts", "services", "routes") for item in retired[key]}
        self.assertFalse(active_ids & retired_ids)
        self.assertFalse(
            any(
                "k8s" in item.lower()
                or "kubernetes" in item.lower()
                or "kube-vip" in item.lower()
                for item in active_ids
            )
        )

    def test_approvals_require_manager_for_mutations(self):
        approvals = yaml.safe_load((ROOT / "automation/policies/approvals.yml").read_text())
        for name, operation in approvals["operations"].items():
            if operation["mutating"]:
                self.assertIn("Manager", operation["roles"], name)
                self.assertTrue(approvals["defaults"]["requires_post_check"])

    def test_audit_json_has_no_secret_values(self):
        command = ["bash", str(ROOT / "automation/scripts/audit-runtime.sh"), "--json"]
        output = subprocess.check_output(command, text=True)
        report = json.loads(output)
        self.assertEqual(report["status"], "not_verified")
        self.assertNotRegex(output.lower(), r"password|token|private_key|client_secret")


if __name__ == "__main__":
    unittest.main()
