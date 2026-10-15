from pathlib import Path
import subprocess
import tempfile
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[2]
DIGEST = 'sha256:c128afca4e026cfc4f33d4cf1c77adc8cb08f01215a3f2bde76a1ecca12b79fd'


class DeployContractTests(unittest.TestCase):
    def test_unenrolled_release_or_truthy_flag_cannot_pass(self):
        catalog = yaml.safe_load((ROOT / 'automation/stacks/catalog.yml').read_text())
        homepage = next(x for x in catalog['services'] if x['id'] == 'homepage')
        for field, value in [('release_template_id', None), ('release_template_id', True),
                             ('release_template_id', -1), ('deployable', 'false')]:
            candidate = yaml.safe_load(yaml.safe_dump(catalog))
            next(x for x in candidate['services'] if x['id'] == 'homepage')[field] = value
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / 'catalog.yml'
                path.write_text(yaml.safe_dump(candidate))
                result = subprocess.run(['bash', str(ROOT / 'automation/scripts/verify-deploy.sh'),
                                         '--catalog', str(path), '--service', 'homepage', '--image', DIGEST,
                                         '--environment', 'production'], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0, (field, value))

    def test_catalog_matches_observed_runtime_not_proposed_limits(self):
        services = {x['id']: x for x in yaml.safe_load((ROOT / 'automation/stacks/catalog.yml').read_text())['services']}
        self.assertEqual([x['id'] for x in services.values() if x['deployable']], ['homepage'])
        self.assertEqual(services['gitlab']['target']['mode'], 'swarm')
        self.assertEqual(services['gitlab']['resources']['memory_mb'], 10240)
        self.assertEqual(services['kubekosh']['networks'], ['homelab-net'])
        self.assertEqual(services['kubekosh']['resources'], {'cpus': '2.00', 'memory_mb': 4096, 'memory_reservation_mb': 1024})
        self.assertEqual(services['stirling-pdf']['resources']['cpus'], '2.00')
        self.assertEqual(services['bds-app']['networks'], ['bds-tunnel-net', 'homelab-net'])
        self.assertEqual(services['macocr-proxy']['networks'], ['edge-http-net', 'homelab-net'])
        self.assertEqual(services['mypocket']['networks'], ['data-net', 'homelab-net', 'mypocket-net', 'mypocket-redis-net'])
        self.assertEqual(services['n8n']['networks'], ['data-net', 'edge-http-net'])
        for name in ('relayhub', 'macocr-proxy', 'mypocket', 'openclaw', 'n8n', 'bds-app'):
            self.assertEqual(services[name]['resources'], {})
            self.assertTrue(services[name]['proposed_resources'])
        self.assertEqual(services['relayhub']['health']['path'], '/readyz')
        self.assertEqual(services['mypocket']['health']['path'], '/api/v1/health')

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
