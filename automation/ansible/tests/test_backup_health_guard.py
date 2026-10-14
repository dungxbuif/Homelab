from pathlib import Path
import os
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]
GUARD = ROOT / 'scripts/backup-health-ssh-guard.sh'


class BackupHealthGuardTests(unittest.TestCase):
    def test_rejects_all_nonliteral_commands(self):
        self.assertTrue(GUARD.is_file())
        for command in ['', 'id', 'backup-health extra', 'backup-health; id',
                        'backup-health\nid', ' backup-health', 'sh', 'scp -t /tmp/x']:
            result = subprocess.run(['bash', str(GUARD)], capture_output=True,
                                    env={**os.environ, 'SSH_ORIGINAL_COMMAND': command})
            self.assertEqual(result.returncode, 2, command)

    def test_only_fixed_unprivileged_helper_is_executable(self):
        self.assertTrue(GUARD.is_file())
        source = GUARD.read_text()
        self.assertIn('exec /usr/bin/sudo -n -u ubuntu /usr/local/libexec/homelab-backup-health', source)
        self.assertNotIn('eval ', source)
        self.assertNotIn('bash -c', source)


if __name__ == '__main__':
    unittest.main()
