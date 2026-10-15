import copy
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('family_network', Path(__file__).resolve().parents[1] / 'scripts/repair-family-network.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class FamilyNetworkTests(unittest.TestCase):
    def test_source_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'target'
            target.write_text('untouched')
            source = Path(directory) / 'link'
            source.symlink_to(target)
            with patch.object(MODULE, 'SOURCE', source):
                with self.assertRaises(OSError): MODULE.source_snapshot()
            self.assertEqual(target.read_text(), 'untouched')

    def exercise_apply(self, root, replace_pg=False, fail_connect=False, edit_source=False):
        source = root / 'compose.yml'
        source.write_text('services:\n  pgbouncer:\n    networks: [proxy_net]\nnetworks:\n  proxy_net:\n    external: true\n')
        source.chmod(0o640)
        receipts = root / 'receipts'
        receipts.mkdir()
        pg = {'Id': 'pg-original', 'NetworkSettings': {'Networks': {'proxy_net': {}}}}
        inspected = 0
        service = {'ID': 'family', 'Version': {'Index': 1}, 'Spec': {'Name': 'family-tree', 'Mode': {'Replicated': {'Replicas': 1}}, 'TaskTemplate': {'Networks': [{'Target': 'edge-id'}]}}}
        calls = []
        def command(argv):
            nonlocal inspected
            calls.append(argv)
            if argv[:3] == ['docker', 'service', 'inspect']: return json.dumps([service]).encode()
            if argv[:2] == ['docker', 'inspect']:
                inspected += 1
                if edit_source and inspected == 3: source.write_text('external edit\n')
                result = copy.deepcopy(pg)
                if replace_pg and inspected > 1: result['Id'] = 'replacement'
                return json.dumps([result]).encode()
            if argv[:3] == ['docker', 'network', 'inspect']:
                return json.dumps([{'Id': 'edge-id' if argv[-1] == 'edge-http-net' else 'data-id', 'Driver': 'overlay', 'Attachable': True, 'Options': {'encrypted': ''}}]).encode()
            if argv[:3] == ['docker', 'network', 'ls']: return b'family-data-net\n'
            if argv[:3] == ['docker', 'network', 'connect'] and fail_connect: raise RuntimeError('injected connection failure')
            return b''
        with patch.object(MODULE, 'SOURCE', source), patch.object(MODULE, 'ROOT', receipts), patch.object(MODULE, 'run', side_effect=command), patch.object(MODULE, 'api'):
            if replace_pg or fail_connect or edit_source:
                with self.assertRaises(RuntimeError): MODULE.repair_locked()
            else: MODULE.repair_locked()
        return source, receipts, calls

    def test_edit_during_final_endpoint_check_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            source, _, _ = self.exercise_apply(Path(directory), edit_source=True)
            self.assertEqual(source.read_text(), 'external edit\n')

    def test_apply_preserves_metadata_and_uses_captured_endpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            source, receipts, calls = self.exercise_apply(Path(directory))
            self.assertEqual(source.stat().st_mode & 0o777, 0o640)
            self.assertEqual(source.stat().st_uid, os.getuid())
            self.assertIn(['docker', 'network', 'connect', '--alias', 'pgbouncer', 'data-id', 'pg-original'], calls)
            receipt = next(receipts.iterdir())
            self.assertTrue((receipt / 'compose-before.metadata.json').exists())

    def test_replaced_endpoint_blocks_source_publication(self):
        with tempfile.TemporaryDirectory() as directory:
            source, _, calls = self.exercise_apply(Path(directory), replace_pg=True)
            self.assertNotIn('family-data-net', source.read_text())
            self.assertFalse(any(c[:3] == ['docker', 'network', 'connect'] for c in calls))

    def test_connection_failure_retains_complete_recovery_intent(self):
        with tempfile.TemporaryDirectory() as directory:
            source, receipts, _ = self.exercise_apply(Path(directory), fail_connect=True)
            receipt = next(receipts.iterdir())
            self.assertEqual((receipt / 'compose-candidate.yml').read_bytes(), source.read_bytes())
            self.assertTrue((receipt / 'compose-candidate.sha256').exists())
            self.assertTrue((receipt / 'pgbouncer-before.json').exists())
            self.assertFalse((receipt / 'result.json').exists())

    def test_preserves_unrelated_config_and_runtime_memberships(self):
        original = {'services': {'pgbouncer': {'networks': ['proxy_net'], 'environment': {'VALUE': '${PRIVATE}'}}, 'other': {'image': 'unchanged'}}, 'networks': {'proxy_net': {'external': True}}}
        saved = copy.deepcopy(original)
        updated = MODULE.compose_candidate(original, {'proxy_net', 'data-net', 'homelab-net'})
        self.assertEqual(original, saved)
        self.assertEqual(set(updated['services']['pgbouncer']['networks']), {'proxy_net', 'data-net', 'homelab-net', 'family-data-net'})
        self.assertEqual(updated['services']['other'], original['services']['other'])
        self.assertEqual(updated['services']['pgbouncer']['environment'], original['services']['pgbouncer']['environment'])
        self.assertEqual(MODULE.compose_candidate(updated, {'proxy_net', 'data-net', 'homelab-net', 'family-data-net'}), updated)

    def test_preserves_mapping_aliases_and_rejects_conflict(self):
        original = {'services': {'pgbouncer': {'networks': {'proxy_net': {'aliases': ['pg']}}}}, 'networks': {}}
        result = MODULE.compose_candidate(original, {'proxy_net'})
        self.assertEqual(result['services']['pgbouncer']['networks']['proxy_net'], {'aliases': ['pg']})
        original['networks']['family-data-net'] = {'driver': 'bridge'}
        with self.assertRaises(ValueError): MODULE.compose_candidate(original, {'proxy_net'})


if __name__ == '__main__': unittest.main()
