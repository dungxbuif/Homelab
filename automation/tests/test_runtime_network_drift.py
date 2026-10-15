import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/compare-runtime-networks.py'


class NetworkDriftTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('network_drift', SCRIPT)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self.policy = {'services': [{'id': 'app', 'host': 'vm100',
            'runtime_service': 'app', 'networks': ['private', 'edge']}]}
        self.rows = [{'id': 'a' * 12, 'name': 'app.1.task', 'service': 'app',
                      'state': 'running', 'networks': 'edge,private'}]
        self.evidence = {'schema_version': 1, 'host': 'vm100', 'task_id': 40,
            'template_id': 4, 'scope': 'host_runtime_only', 'inventory_complete': False,
            'observed_at': '2026-10-15T04:32:47+00:00', 'report': {
                'schema_version': 1, 'scope': 'host_runtime_only',
                'inventory_complete': False, 'collection_complete': True,
                'observed_at': '2026-10-15T04:32:47+00:00', 'probes': {}}}

    def run_report(self):
        self.evidence['report']['probes']['container_inventory'] = {
            'output': '\n'.join(json.dumps(row) for row in self.rows)}
        return self.module.compare(self.policy, self.evidence,
                                   now='2026-10-15T04:33:00+00:00')

    def test_matching_networks_never_claims_global_completeness(self):
        result = self.run_report()
        self.assertEqual(result['status'], 'match')
        self.assertFalse(result['inventory_complete'])
        self.assertEqual(result['scope'], 'rootful_container_network_membership')

    def test_network_drift_and_missing(self):
        self.rows[0]['networks'] = 'private,wrong'
        result = self.run_report()
        self.assertEqual(result['status'], 'drift')
        self.assertEqual(result['findings'][0]['extra_networks'], ['wrong'])
        self.assertEqual(result['findings'][0]['missing_networks'], ['edge'])
        self.rows = []
        self.assertEqual(self.run_report()['findings'][0]['kind'], 'missing_running_service')

    def test_exited_tasks_ignored_but_unknown_created_reported(self):
        old = dict(self.rows[0], id='b' * 12, state='exited', networks='old')
        self.rows.append(old)
        self.assertEqual(self.run_report()['status'], 'match')
        self.rows.append(dict(old, id='c' * 12, state='created', service='unknown'))
        self.assertEqual(self.run_report()['findings'][0]['kind'], 'unknown_nonterminal_container')

    def test_every_running_replica_compared(self):
        self.rows.append(dict(self.rows[0], id='b' * 12, networks='wrong'))
        self.assertEqual(len(self.run_report()['findings']), 1)

    def test_unbound_is_not_verified_and_duplicate_binding_rejected(self):
        del self.policy['services'][0]['runtime_service']
        self.assertEqual(self.run_report()['status'], 'not_verified')
        self.policy['services'][0]['runtime_service'] = 'app'
        self.policy['services'].append(dict(self.policy['services'][0], id='other'))
        with self.assertRaises(ValueError):
            self.run_report()

    def test_invalid_provenance_stale_or_duplicate_container_rejected(self):
        for field, value in [('template_id', 5), ('inventory_complete', True),
                             ('observed_at', '2026-10-14T04:32:47+00:00')]:
            original = copy.deepcopy(self.evidence)
            self.evidence[field] = value
            with self.assertRaises(ValueError):
                self.run_report()
            self.evidence = original
        self.rows.append(dict(self.rows[0]))
        with self.assertRaises(ValueError):
            self.run_report()

    def test_malformed_or_failed_probe_rejected(self):
        self.run_report()
        for probe in ({'output': '{'}, {'output': '', 'error': 'timeout'}, {'output': 42}):
            self.evidence['report']['probes']['container_inventory'] = probe
            with self.assertRaises(ValueError):
                self.module.compare(self.policy, self.evidence, now='2026-10-15T04:33:00+00:00')

    def test_cli_malformed_yaml_is_sanitized_not_verified(self):
        with tempfile.TemporaryDirectory() as tmp:
            active = Path(tmp) / 'active.yaml'
            active.write_text('services: [PRIVATE_SENTINEL')
            result = subprocess.run([sys.executable, str(SCRIPT), '--active', str(active),
                                     '--observed', str(Path(tmp) / 'unused.json')],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(json.loads(result.stdout)['status'], 'not_verified')
            self.assertEqual(result.stderr, '')
            self.assertNotIn('PRIVATE_SENTINEL', result.stdout)


if __name__ == '__main__':
    unittest.main()
