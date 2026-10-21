import importlib.util
import json
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
        with patch.object(module.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, '', '')) as run:
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

    def test_limits_select_only_resource_fields_for_known_ids(self):
        module = self.module()
        inventory = {'output': json.dumps({'id': 'a' * 12}) + '\n'}
        with patch.object(module.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, '{}\n', '')) as run:
            result = module.collect_limits(inventory)
        self.assertEqual(result['output'], '{}\n')
        argv = run.call_args.args[0]
        self.assertEqual(argv[:3], ('/usr/bin/docker', 'inspect', '--format'))
        self.assertEqual(argv[-1], 'a' * 12)
        for field in ['Memory', 'MemoryReservation', 'MemorySwap', 'NanoCpus', 'CpuQuota', 'CpuPeriod', 'CpuShares', 'PidsLimit']:
            self.assertIn('.HostConfig.' + field, argv[3])
        for forbidden in ['.Env', '.Labels', '.Mounts', '.Cmd', '{{json .}}', '{{json .HostConfig}}']:
            self.assertNotIn(forbidden, argv[3])

    def test_limits_reject_unknown_ids_and_preserve_failure(self):
        module = self.module()
        with patch.object(module.subprocess, 'run') as run:
            for raw in ['not-json', '{"id":"--help"}', '{"id":""}']:
                self.assertIn('error', module.collect_limits({'output': raw}))
            self.assertEqual(module.collect_limits({'error': 'timeout'}), {'error': 'timeout'})
            self.assertEqual(module.collect_limits({'output': ''}), {'output': ''})
            run.assert_not_called()

    def test_limits_follow_inventory_before_slow_stats_probe(self):
        module = self.module()
        def run(argv, **kwargs):
            output = json.dumps({'id': 'a' * 12}) if argv == module.PROBES['container_inventory'] else ''
            return subprocess.CompletedProcess(argv, 0, output, '')
        with patch.object(module.subprocess, 'run', side_effect=run) as mocked:
            module.collect()
        calls = [x.args[0] for x in mocked.call_args_list]
        inventory_at = calls.index(module.PROBES['container_inventory'])
        self.assertEqual(calls[inventory_at + 1][1], 'inspect')

    def test_limits_ignore_stopped_tasks_and_retry_transient_disappearance(self):
        module = self.module()
        inventories = iter([
            json.dumps({'id': 'a' * 12, 'state': 'exited'}) + '\n' +
            json.dumps({'id': 'b' * 12, 'state': 'running'}) + '\n',
            json.dumps({'id': 'b' * 12, 'state': 'running'}) + '\n',
        ])
        inspect_calls = 0

        def run(argv, **kwargs):
            nonlocal inspect_calls
            if argv == module.PROBES['container_inventory']:
                return subprocess.CompletedProcess(argv, 0, next(inventories), '')
            if len(argv) > 1 and argv[1] == 'inspect':
                inspect_calls += 1
                if inspect_calls == 1:
                    return subprocess.CompletedProcess(argv, 1, '', 'No such object')
                return subprocess.CompletedProcess(argv, 0, '{}\n', '')
            return subprocess.CompletedProcess(argv, 0, '', '')

        with patch.object(module.subprocess, 'run', side_effect=run) as mocked:
            result = module.collect()

        self.assertTrue(result['collection_complete'])
        self.assertEqual(inspect_calls, 2)
        inspect_argv = [call.args[0] for call in mocked.call_args_list
                        if len(call.args[0]) > 1 and call.args[0][1] == 'inspect']
        self.assertEqual(inspect_argv[0][-1], 'b' * 12)
        self.assertEqual(inspect_argv[1][-1], 'b' * 12)

    def test_failed_command_exposes_only_allowlisted_diagnostic(self):
        module = self.module()
        with patch.object(module.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1, '', 'Error: No such object: fixture-secret')):
            result = module.execute_probe(('/usr/bin/docker', 'inspect'))
        self.assertEqual(result['reason'], 'object_disappeared')
        self.assertNotIn('fixture-secret', str(result))

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

    def test_inventory_probe_selects_metadata_without_secrets(self):
        module = self.module()
        probe = module.PROBES['container_inventory']
        self.assertEqual(probe[:4], ('/usr/bin/docker', 'ps', '-a', '--format'))
        template = probe[4]
        for field in ['.ID', '.Names', '.Image', '.State', '.Networks', '.Ports']:
            self.assertIn('{{json ' + field + '}}', template)
        for label in ['com.docker.swarm.service.name', 'com.docker.compose.project']:
            self.assertIn(label, template)
        for forbidden in ['.Command', '.Env', '.Labels', '.Mounts', '{{json .}}']:
            self.assertNotIn(forbidden, template)

    def test_swarm_probe_is_read_only_and_worker_safe(self):
        module = self.module()
        calls = []

        def run(argv, **kwargs):
            calls.append(argv)
            if argv[1:3] == ('info', '--format'):
                return subprocess.CompletedProcess(argv, 0, 'false\n', '')
            return subprocess.CompletedProcess(argv, 0, '', '')

        with patch.object(module.subprocess, 'run', side_effect=run):
            result = module.collect_swarm_services()
        self.assertEqual(json.loads(result['output']), {'manager': False, 'services': []})
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][:3], ('/usr/bin/docker', 'info', '--format'))


if __name__ == '__main__':
    unittest.main()
