from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[3]
PLAY = ROOT / "automation/ansible/playbooks/backup-instance-runtime-deploy.yml"
ENROLL = ROOT / "automation/ansible/playbooks/backup-instance-enroll.yml"


class BackupInstanceDeployContractTests(unittest.TestCase):
    def test_runtime_deploy_is_explicit_and_lock_aware(self):
        source = PLAY.read_text()
        self.assertIn("backup_instance_runtime_deploy_approved", source)
        self.assertIn("/run/lock/homelab-backup.lock", source)
        self.assertIn("run-instance-backup.py", source)
        self.assertIn("homelab-backup-database-instances.timer", source)
        self.assertIn("daemon_reload", source)
        self.assertIn("enable", source)
        self.assertIn("- name: Publish the candidate atomically under the backup lock\n      become: true", source)

    def test_enrollment_publishes_policy_with_catalog_generation(self):
        source = ENROLL.read_text()
        self.assertIn("Stage the reviewed policy catalog", source)
        self.assertIn("db-instance-default", (ROOT / "backup/policies.yaml").read_text())
        self.assertIn("previous-policies.yaml", source)
        self.assertIn("Path(sys.argv[1]) / 'policies.yaml'", source)
        self.assertIn("/run/lock/homelab-backup.lock", source)
        self.assertIn("Verify the active generation resolves", source)


if __name__ == "__main__":
    unittest.main()
