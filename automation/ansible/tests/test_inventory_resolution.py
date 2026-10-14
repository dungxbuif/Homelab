"""Validate the actual Ansible inventory loader, not just YAML shape."""
import json
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class InventoryResolutionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        result = subprocess.run(
            ["ansible-inventory", "-i", str(ROOT / "inventories/production/hosts.yml"), "--list"],
            cwd="/tmp", capture_output=True, text=True, check=True,
        )
        cls.hosts = json.loads(result.stdout)["_meta"]["hostvars"]

    def test_roles_are_loaded_for_every_host(self):
        for host, role in {
            "pi5": "edge_datastore_swarm_manager",
            "vm100": "production_worker",
            "vps-gateway": "public_gateway",
        }.items():
            with self.subTest(host=host):
                self.assertEqual(self.hosts[host].get("automation_host_role"), role)

    def test_mutations_and_escalation_are_disabled_by_default(self):
        for host, values in self.hosts.items():
            with self.subTest(host=host):
                self.assertIs(values.get("ansible_become"), False)
                for flag in ["apply_baseline", "manage_docker", "manage_swarm",
                             "manage_ssh", "manage_logging", "manage_swap"]:
                    self.assertIs(values.get("automation_" + flag), False)

    def test_swarm_expectations_are_host_specific(self):
        self.assertIs(self.hosts["vps-gateway"].get("automation_expected_swarm"), False)
        self.assertIs(self.hosts["pi5"].get("automation_expected_swarm"), True)
        self.assertIs(self.hosts["vm100"].get("automation_expected_swarm"), True)

    def test_bootstrap_does_not_grant_root_equivalent_command_access(self):
        base = (ROOT / "roles/base/tasks/main.yml").read_text()
        self.assertNotIn("NOPASSWD", base)
        self.assertNotIn("/etc/sudoers", base)


if __name__ == "__main__":
    unittest.main()
