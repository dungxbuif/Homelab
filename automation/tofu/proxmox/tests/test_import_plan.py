import copy
import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[3] / 'scripts' / 'check-vm100-plan.py'
spec = importlib.util.spec_from_file_location('plan_guard', SCRIPT)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


class ImportPlanTest(unittest.TestCase):
    def setUp(self):
        self.plan = {'format_version': '1.2', 'resource_changes': [{
            'address': 'proxmox_virtual_environment_vm.vm100', 'mode': 'managed',
            'change': {'actions': ['no-op'], 'importing': {'id': 'pve/100'},
                       'after': {'vm_id': 100, 'node_name': 'pve'}},
        }]}

    def test_import_only_passes(self):
        self.assertEqual(guard.check(self.plan, 'import'), [])

    def test_all_mutations_fail(self):
        for actions in [['update'], ['delete'], ['create'], ['delete', 'create'], ['read']]:
            plan = copy.deepcopy(self.plan)
            plan['resource_changes'][0]['change']['actions'] = actions
            self.assertTrue(guard.check(plan, 'import'), actions)

    def test_wrong_import_id_fails(self):
        self.plan['resource_changes'][0]['change']['importing']['id'] = 'pve/101'
        self.assertTrue(guard.check(self.plan, 'import'))

    def test_missing_target_fails(self):
        self.plan['resource_changes'] = []
        self.assertTrue(guard.check(self.plan, 'import'))

    def test_extra_resource_fails(self):
        extra = copy.deepcopy(self.plan['resource_changes'][0])
        extra['address'] = 'proxmox_virtual_environment_vm.other'
        self.plan['resource_changes'].append(extra)
        self.assertTrue(guard.check(self.plan, 'import'))

    def test_unknown_and_incomplete_inputs_fail(self):
        for plan in [{}, [], {'format_version': '2.0'}, {**self.plan, 'errored': True},
                     {**self.plan, 'complete': False}, {**self.plan, 'deferred_changes': [{}]}]:
            self.assertTrue(guard.check(plan, 'import'))

    def test_noop_mode_requires_no_import(self):
        self.assertTrue(guard.check(self.plan, 'noop'))
        del self.plan['resource_changes'][0]['change']['importing']
        self.assertEqual(guard.check(self.plan, 'noop'), [])
        self.assertTrue(guard.check(self.plan, 'import'))

    def test_missing_or_wrong_target_values_fail(self):
        for after in [None, {}, {'vm_id': 101, 'node_name': 'pve'},
                      {'vm_id': 100, 'node_name': 'other'}]:
            self.plan['resource_changes'][0]['change']['after'] = after
            self.assertTrue(guard.check(self.plan, 'import'))


if __name__ == '__main__':
    unittest.main()
