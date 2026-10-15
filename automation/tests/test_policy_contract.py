#!/usr/bin/env python3
import json
import subprocess
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]


class PolicyContractTest(unittest.TestCase):
    def test_pi_vm_services_have_unique_explicit_runtime_bindings(self):
        active = yaml.safe_load((ROOT / 'automation/policies/active-runtime.yaml').read_text())
        bindings = set()
        for service in active['services']:
            if service['host'] not in ('pi5', 'vm100'):
                continue
            keys = [key for key in ('runtime_container', 'runtime_service') if key in service]
            self.assertEqual(len(keys), 1, service['id'])
            identity = (service['host'], keys[0], service[keys[0]])
            self.assertNotIn(identity, bindings)
            bindings.add(identity)
        self.assertEqual(len(bindings), 47)

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
        self.assertFalse(any("k8s" in item['id'].lower() or "kube" in item['id'].lower()
                             for item in active['hosts']))
        self.assertFalse(any(item['class'] in ['kubernetes', 'kube-vip', 'kubernetes_node']
                             for item in active['services']))

    def test_observed_application_and_monitoring_components_are_not_omitted(self):
        active = yaml.safe_load((ROOT / 'automation/policies/active-runtime.yaml').read_text())
        services = {item['id']: item for item in active['services']}
        expected = {
            'family-tree': ('vm100', {'edge-http-net', 'family-data-net'}),
            'mypocket-api': ('vm100', {'data-net', 'homelab-net', 'mypocket-net', 'mypocket-redis-net'}),
            'mypocket-worker': ('vm100', {'data-net', 'homelab-net', 'mypocket-net', 'mypocket-redis-net'}),
            'macocr-proxy': ('vm100', {'edge-http-net', 'homelab-net'}),
            'n8n': ('vm100', {'data-net', 'edge-http-net'}),
            'k8s-syntax': ('vm100', {'homelab-net'}),
            'relayhub-worker': ('vm100', {'relayhub-net'}),
            'relayhub-nats': ('vm100', {'relayhub-net'}),
            'relayhub-redis': ('vm100', {'relayhub-net'}),
            'couchloom-postgres': ('vm100', {'couchloom-internal'}),
            'relayhub-dedicated-postgres': ('pi5', {'relayhub_relayhub'}),
            'alertmanager': ('pi5', {'proxy_net'}),
            'victoriametrics': ('pi5', {'proxy_net'}),
            'pgadmin': ('pi5', {'edge-http-net', 'homelab-net', 'proxy_net'}),
        }
        for name, (host, networks) in expected.items():
            self.assertEqual(services[name]['host'], host)
            self.assertEqual(set(services[name]['networks']), networks)
        self.assertEqual(services['k8s-syntax']['class'], 'learning_app')
        self.assertTrue(services['relayhub-dedicated-postgres']['ownership_review_required'])
        self.assertEqual(services['adguardhome']['observed_host_ports'], [53, 81])
        self.assertFalse(active['inventory_complete'])

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
