from pathlib import Path
import subprocess
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[2]
DIGEST = 'sha256:c128afca4e026cfc4f33d4cf1c77adc8cb08f01215a3f2bde76a1ecca12b79fd'


class DeployContractTests(unittest.TestCase):
    def verify(self, digest):
        return subprocess.run(['bash', str(ROOT / 'automation/scripts/verify-deploy.sh'),
                               '--service', 'homepage', '--image', digest,
                               '--environment', 'production'], capture_output=True, text=True)

    def test_only_catalog_digest_passes(self):
        self.assertEqual(self.verify(DIGEST).returncode, 0)
        result = self.verify('sha256:' + 'a' * 64)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('approved catalog digest', result.stderr)

    def test_homepage_catalog_matches_released_boundary(self):
        catalog = yaml.safe_load((ROOT / 'automation/stacks/catalog.yml').read_text())
        homepage = next(x for x in catalog['services'] if x['id'] == 'homepage')
        self.assertEqual(homepage['image']['repository'], 'registry-gitlab.dungxbuif.com/dungxbuif/homepage')
        self.assertEqual(homepage['image']['digest'], DIGEST)
        self.assertEqual(homepage['networks'], ['edge-http-net'])
        self.assertEqual(homepage['resources'], {})
        self.assertEqual(homepage['release_template_id'], 6)


if __name__ == '__main__':
    unittest.main()
