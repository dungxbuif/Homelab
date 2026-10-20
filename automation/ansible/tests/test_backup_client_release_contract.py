from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[3]
PLAY = ROOT / "automation/ansible/playbooks/backup-client-release.yml"


class BackupClientReleaseContractTests(unittest.TestCase):
    def test_release_is_approved_and_writes_controller_post_check(self):
        source = PLAY.read_text()
        self.assertIn("backup_client_release_approved", source)
        self.assertIn("client_files:", source)
        for filename in (
            "prepare_rclone_workdir.py",
            "run_restic_container.py",
            "restic-lib.sh",
            "upload-restic.sh",
            "verify-database-payload.py",
        ):
            self.assertIn(filename, source)
        self.assertIn("dest: artifacts/backup-client-release.json", source)
        self.assertIn("delegate_to: localhost", source)
        self.assertIn("inventory_hostname == ansible_play_hosts_all[0]", source)

    def test_pi_release_publishes_bounded_executor_bundle(self):
        source = PLAY.read_text()
        for filename in ("run-pi-capped.sh", "pi-executor.sh", "pi-ssh-guard.sh"):
            self.assertIn(f"src: {filename}", source)
        self.assertIn("dest: /home/dungxbuif/.local/sbin/homelab-backup-executor", source)
        self.assertIn("dest: /home/dungxbuif/.local/sbin/homelab-backup-ssh-guard", source)
        self.assertIn("inventory_hostname == 'pi5'", source)
        self.assertIn("/ssd-data/infra/backup-runner/app/automation/backup-runner/run-pi-capped.sh", source)

    def test_retention_handles_only_stale_locks(self):
        source = (ROOT / "backup/scripts/verify-retention.sh").read_text()
        self.assertIn("stale Restic lock detected with no local Restic/rclone process", source)
        self.assertIn("restic_run unlock", source)
        self.assertIn("pgrep -x restic", source)
        self.assertIn("pgrep -x rclone", source)


if __name__ == "__main__":
    unittest.main()
