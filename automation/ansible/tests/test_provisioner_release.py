from pathlib import Path
import unittest
import yaml

PLAY = Path(__file__).resolve().parents[1] / 'playbooks/provisioner-release.yml'


class ProvisionerReleaseTests(unittest.TestCase):
    def test_rollback_requires_current_image_to_be_this_release(self):
        play = yaml.safe_load(PLAY.read_text())[0]
        block = next(t for t in play['tasks'] if 'rescue' in t)
        rollback = next(t for t in block['rescue'] if 'ansible.builtin.command' in t
                        and 'rollback' in t['ansible.builtin.command']['argv'])
        self.assertIn('provisioner_update_attempted', str(rollback['when']))
        self.assertIn('provisioner_observed_image.stdout == provisioner_image', str(rollback['when']))

    def test_receipt_is_durable_and_registry_auth_is_cleaned(self):
        play = yaml.safe_load(PLAY.read_text())[0]
        receipt = next(t for t in play['tasks'] if t.get('register') == 'release_receipt')
        self.assertEqual(receipt['ansible.builtin.tempfile'].get('path'),
                         '/ssd-data/infra/provisioner/releases')
        block = next(t for t in play['tasks'] if 'always' in t)
        self.assertEqual(block['always'][0]['ansible.builtin.file']['state'], 'absent')


if __name__ == '__main__':
    unittest.main()
