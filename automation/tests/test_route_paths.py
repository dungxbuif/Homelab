import importlib.util
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/probe-route-paths.py'


class RoutePathsTest(unittest.TestCase):
    def setUp(self):
        self.assertTrue(SCRIPT.exists(), 'repeatable route path probe is missing')
        spec = importlib.util.spec_from_file_location('route_paths', SCRIPT)
        self.probe = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.probe)

    def test_auth_is_reachable_not_network_denied(self):
        for code in ('200', '302', '401'):
            with patch.object(self.probe.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, code, 'SECRET')):
                result = self.probe.probe('pgadmin.dungxbuif.com', '/', '103.82.21.202')
            self.assertEqual(result['observation'], 'http_response')
            self.assertNotIn('SECRET', str(result))

    def test_tls_failure_is_incomplete(self):
        with patch.object(self.probe.subprocess, 'run', return_value=subprocess.CompletedProcess([], 60, '000', 'SECRET')):
            result = self.probe.probe('semaphore.dungxbuif.com', '/', '103.82.21.202')
        self.assertEqual(result['observation'], 'tls_error')
        self.assertFalse(result['transport_complete'])

    def test_request_is_bounded_and_has_no_proxy_config_redirects_or_credentials(self):
        with patch.object(self.probe.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, '403', '')) as run:
            result = self.probe.probe('semaphore.dungxbuif.com', '/', '103.82.21.202')
        args = run.call_args.args[0]
        self.assertEqual(args[:2], ['curl', '--disable'])
        self.assertIn('--noproxy', args)
        self.assertIn('--max-time', args)
        self.assertNotIn('-k', args)
        self.assertNotIn('--location', args)
        self.assertNotIn('--user', args)
        self.assertEqual(result['observation'], 'http_response')
        self.assertNotIn('policy_pass', result)

    def test_timeouts_and_bad_output_are_incomplete(self):
        for outcome in (subprocess.TimeoutExpired('curl', 20), FileNotFoundError('curl')):
            with patch.object(self.probe.subprocess, 'run', side_effect=outcome):
                self.assertFalse(self.probe.probe('a.example.com', '/', '10.10.0.5')['transport_complete'])
        with patch.object(self.probe.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, 'SECRET', '')):
            result = self.probe.probe('a.example.com', '/', '10.10.0.5')
        self.assertFalse(result['transport_complete'])
        self.assertNotIn('SECRET', str(result))

    def test_aliases_preserved_internal_skipped(self):
        routes = [{'id': 'sync', 'hostnames': ['a.example.com', 'b.example.com'], 'health_path': '/', 'exposure': 'lan'},
                  {'id': 'internal', 'hostnames': ['private.example.com'], 'health_path': '/', 'exposure': 'internal'}]
        self.assertEqual(len(list(self.probe.targets(routes))), 2)

    def test_unsafe_inputs_rejected_before_request(self):
        for hostname, path, address in [('bad`host', '/', '10.10.0.5'), ('a.example.com', '//evil', '10.10.0.5'),
                                         ('a.example.com', '/?token=secret', '10.10.0.5'), ('a.example.com', '/', 'evil:443')]:
            with patch.object(self.probe.subprocess, 'run') as run:
                with self.assertRaises(ValueError):
                    self.probe.probe(hostname, path, address)
                run.assert_not_called()


if __name__ == '__main__':
    unittest.main()
