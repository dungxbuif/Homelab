"""Check the audit's safe collection and artifact boundary."""
from pathlib import Path
import unittest
import yaml

PLAY = Path(__file__).resolve().parents[1] / "playbooks/audit.yml"


class AuditArtifactTest(unittest.TestCase):
    def test_backup_journal_is_bounded_and_uses_exact_units(self):
        tasks = yaml.safe_load((PLAY.parent / "backup-audit.yml").read_text())[0]["tasks"]
        commands = [task["ansible.builtin.command"]["argv"]
                    for task in tasks if "ansible.builtin.command" in task]
        journal = next(argv for argv in commands if "journalctl" in argv)
        self.assertEqual(journal[:3], ["timeout", "20s", "journalctl"])
        self.assertNotIn("homelab-backup@*", journal)

    def test_artifact_is_local_private_and_partial(self):
        tasks = yaml.safe_load(PLAY.read_text())[0]["tasks"]
        exports = [task for task in tasks if "ansible.builtin.copy" in task]
        self.assertEqual(len(exports), 1)
        task = exports[0]
        self.assertEqual(task["delegate_to"], "localhost")
        self.assertFalse(task["become"])
        self.assertEqual(task["ansible.builtin.copy"]["mode"], "0600")
        self.assertIn("audit_artifact_dir", task["when"])
        records = [task["ansible.builtin.set_fact"]["audit_record"]
                   for task in tasks if "ansible.builtin.set_fact" in task]
        self.assertEqual(records[0]["scope"], "host_runtime_only")
        self.assertEqual(records[0]["inventory_complete"], False)

    def test_only_allowlisted_docker_reads(self):
        tasks = yaml.safe_load(PLAY.read_text())[0]["tasks"]
        commands = [task["ansible.builtin.command"]["argv"]
                    for task in tasks if "ansible.builtin.command" in task]
        docker = [argv for argv in commands if argv[0] == "docker"]
        self.assertIn(["/bin/cat", "/proc/swaps"], commands)
        self.assertTrue(any(argv[1] == "ps" for argv in docker))
        self.assertTrue(any(argv[1:3] == ["network", "ls"] for argv in docker))
        self.assertTrue(any(argv[1:3] == ["stats", "--no-stream"] for argv in docker))
        self.assertFalse(any("inspect" in argv for argv in docker))
        for task in tasks:
            if "ansible.builtin.command" in task:
                self.assertFalse(task["changed_when"])


if __name__ == "__main__":
    unittest.main()
