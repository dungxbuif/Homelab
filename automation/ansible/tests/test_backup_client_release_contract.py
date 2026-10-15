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


if __name__ == "__main__":
    unittest.main()
