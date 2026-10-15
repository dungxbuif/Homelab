from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[3]
PLAY = ROOT / "automation/ansible/playbooks/backup-instance-runtime-deploy.yml"


class BackupInstanceDeployContractTests(unittest.TestCase):
    def test_runtime_deploy_is_explicit_and_lock_aware(self):
        source = PLAY.read_text()
        self.assertIn("backup_instance_runtime_deploy_approved", source)
        self.assertIn("/run/lock/homelab-backup.lock", source)
        self.assertIn("run-instance-backup.py", source)
        self.assertIn("homelab-backup-database-instances.timer", source)
        self.assertIn("daemon_reload", source)
        self.assertIn("enable", source)


if __name__ == "__main__":
    unittest.main()
