import unittest
from pathlib import Path

import yaml
from jinja2 import Environment, StrictUndefined

ROOT = Path(__file__).resolve().parents[3]


class RunnerStackTest(unittest.TestCase):
    def test_runner_has_no_host_privileges_and_uses_vm100(self):
        source = (ROOT / 'automation/ansible/templates/semaphore-runner-stack.yml.j2').read_text()
        rendered = Environment(undefined=StrictUndefined).from_string(source).render(
            semaphore_runner_image='registry.example/runner@sha256:' + 'a' * 64,
            semaphore_runner_secret='runner-config-test',
        )
        stack = yaml.safe_load(rendered)
        runner = stack['services']['runner']
        self.assertEqual(runner['user'], '1001:1001')
        self.assertEqual(runner['dns'], ['10.10.0.5'])
        for field in ['ports', 'volumes', 'privileged', 'network_mode']:
            self.assertNotIn(field, runner)
        self.assertEqual(runner['deploy']['placement']['constraints'], ['node.hostname == vm100-prod'])
        self.assertEqual(runner['deploy']['replicas'], 1)
        self.assertEqual(runner['secrets'][0]['mode'], 0o400)
        self.assertEqual(runner['secrets'][0]['uid'], '1001')
        self.assertEqual(stack['secrets']['runner-config-test'], {'external': True})


if __name__ == '__main__':
    unittest.main()
