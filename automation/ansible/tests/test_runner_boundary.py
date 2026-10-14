import json
from pathlib import Path
import tomllib
import unittest

from jinja2 import Environment, StrictUndefined


class RunnerBoundaryTest(unittest.TestCase):
    def test_jobs_cannot_mount_production_socket(self):
        template = Path(__file__).resolve().parents[1] / 'templates/ci-runner-config.toml.j2'
        env = Environment(undefined=StrictUndefined)
        env.filters['to_json'] = json.dumps
        rendered = env.from_string(template.read_text()).render(
            runner_credential={'id': 1, 'token': 'dummy-token-for-render-test'})
        data = tomllib.loads(rendered)
        self.assertEqual(data['concurrent'], 1)
        docker = data['runners'][0]['docker']
        self.assertFalse(docker['privileged'])
        self.assertEqual(docker['volumes'], ['/certs/client', '/cache'])
        self.assertEqual(docker['allowed_services'], docker['allowed_privileged_services'])
        self.assertTrue(all(x.endswith(':27.5.1-dind-rootless') for x in docker['allowed_services']))
        self.assertNotIn('*', ''.join(docker['allowed_images']))


if __name__ == '__main__':
    unittest.main()
