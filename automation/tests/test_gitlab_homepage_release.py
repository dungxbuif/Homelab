from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts' / 'gitlab-homepage-release.sh'


class GitLabHomepageReleaseTests(unittest.TestCase):
    def test_script_is_shell_valid_and_uses_fixed_forced_command_boundary(self):
        result = subprocess.run(['bash', '-n', str(SCRIPT)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        source = SCRIPT.read_text()
        self.assertIn('verify-deploy.sh', source)
        self.assertIn('homelab-homepage-release@10.10.0.5', source)
        self.assertIn('homepage-release "$HOMEPAGE_IMAGE_DIGEST"', source)
        self.assertIn('StrictHostKeyChecking=yes', source)
        self.assertIn('notify-homepage-release.py', source)
        self.assertIn('HOMELAB_MEZON_WEBHOOK_URL_FILE', source)
        self.assertNotIn('HOMELAB_MEZON_WEBHOOK_URL:?', source)
        self.assertNotIn('ssh root@', source)
        self.assertNotIn('bash -s', source)


if __name__ == '__main__':
    unittest.main()
