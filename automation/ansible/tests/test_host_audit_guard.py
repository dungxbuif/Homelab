from pathlib import Path
import os
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]
GUARD = ROOT / 'scripts/host-audit-ssh-guard.sh'


class HostAuditGuardTests(unittest.TestCase):
    def test_rejects_nonliteral_commands(self):
        self.assertTrue(GUARD.is_file())
        for command in ['', 'id', 'host-audit extra', 'host-audit; id',
                        'host-audit\nid', ' host-audit', 'sh', 'scp -t /tmp/x']:
            result = subprocess.run(['bash', str(GUARD)], capture_output=True,
                                    env={**os.environ, 'SSH_ORIGINAL_COMMAND': command})
            self.assertEqual(result.returncode, 2, command)

    def test_only_fixed_helper_as_unprivileged_owner(self):
        self.assertTrue(GUARD.is_file())
        source = GUARD.read_text()
        self.assertIn('exec /usr/bin/sudo -n -u ubuntu /usr/local/libexec/homelab-host-observer', source)
        self.assertNotIn('eval ', source)
        self.assertNotIn('bash -c', source)


if __name__ == '__main__':
    unittest.main()
