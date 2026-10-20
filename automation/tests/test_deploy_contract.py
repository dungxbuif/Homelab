import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[2]
DIGEST = 'sha256:c128afca4e026cfc4f33d4cf1c77adc8cb08f01215a3f2bde76a1ecca12b79fd'


class DeployContractTests(unittest.TestCase):
    def setUp(self):
        self.test_env = os.environ.copy()
        self.test_env["PYTHON_BIN"] = sys.executable

    def run_verify(self, *args):
        return subprocess.run(
            ['bash', str(ROOT / 'automation/scripts/verify-deploy.sh'), *args],
            capture_output=True,
            text=True,
            env=self.test_env,
        )

    def test_family_runtime_is_catalogued_but_not_release_ready(self):
        services = {x['id']: x for x in yaml.safe_load((ROOT / 'automation/stacks/catalog.yml').read_text())['services']}
        family = services['family-tree']
        self.assertEqual(family['target'], {'host': 'vm100', 'mode': 'swarm'})
        self.assertEqual(set(family['networks']), {'edge-http-net', 'family-data-net'})
        self.assertEqual(family['routes'], ['family'])
        self.assertEqual(family['resources'], {})
        self.assertIsNone(family['image']['digest'])
        self.assertFalse(family['deployable'])
        self.assertIsNone(family['rollback_image'])
        self.assertEqual(family['source_mount'], '/opt/apps/family-tree/src')
        result = self.run_verify('--service', 'family-tree', '--image', DIGEST,
                                 '--environment', 'production')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('not release-ready', result.stderr)

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
                result = self.run_verify('--catalog', str(path), '--service', 'homepage', '--image', DIGEST,
                                         '--environment', 'production')
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
        return self.run_verify('--service', 'homepage', '--image', digest,
                               '--environment', 'production')

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
