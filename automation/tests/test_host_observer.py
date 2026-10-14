import importlib.util
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


class HostObserverTests(unittest.TestCase):
    def module(self):
        path = ROOT / 'scripts/host-observer.py'
        self.assertTrue(path.is_file())
        spec = importlib.util.spec_from_file_location('host_observer', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_only_fixed_read_commands_and_environment(self):
        module = self.module()
        with patch.object(module.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, 'ok', '')) as run:
            result = module.collect()
        self.assertTrue(result['collection_complete'])
        self.assertFalse(result['inventory_complete'])
        for call in run.call_args_list:
            argv = call.args[0]
            self.assertTrue(argv[0].startswith('/usr/bin/'))
            self.assertNotIn('inspect', argv)
            self.assertNotIn('logs', argv)
            self.assertNotIn('exec', argv)
            self.assertNotIn('sudo', argv)
            self.assertLessEqual(call.kwargs['timeout'], 30)
            self.assertEqual(call.kwargs['env']['DOCKER_HOST'], 'unix:///var/run/docker.sock')
            self.assertNotIn('SSH_AUTH_SOCK', call.kwargs['env'])

    def test_failed_probe_does_not_become_healthy_or_leak_stderr(self):
        module = self.module()
        with patch.object(module.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1, '', 'fixture-secret')):
            result = module.collect()
        self.assertFalse(result['collection_complete'])
        self.assertNotIn('fixture-secret', str(result))
        self.assertTrue(all(x['error'] == 'command_failed' for x in result['probes'].values()))

    def test_timeout_is_explicit(self):
        module = self.module()
        with patch.object(module.subprocess, 'run', side_effect=subprocess.TimeoutExpired('fixed', 30)):
            result = module.collect()
        self.assertFalse(result['collection_complete'])
        self.assertTrue(all(x['error'] == 'timeout' for x in result['probes'].values()))

    def test_arguments_rejected_before_any_probe(self):
        module = self.module()
        with patch.object(module.sys, 'argv', ['host-observer', 'docker']), patch.object(module, 'collect') as collect:
            self.assertEqual(module.main(), 2)
        collect.assert_not_called()

    def test_missing_executable_is_not_silently_skipped(self):
        module = self.module()
        with patch.object(module.subprocess, 'run', side_effect=FileNotFoundError('private-path')):
            result = module.collect()
        self.assertFalse(result['collection_complete'])
        self.assertNotIn('private-path', str(result))
        self.assertTrue(all(x['error'] == 'command_unavailable' for x in result['probes'].values()))


if __name__ == '__main__':
    unittest.main()
