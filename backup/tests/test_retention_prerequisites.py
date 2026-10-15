import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / 'automation/backup-runner/wait-retention-prerequisites.py'


class PrerequisiteTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('retention_gate', SCRIPT)
        self.gate = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.gate)
        self.good = {'LoadState': 'loaded', 'ActiveState': 'inactive', 'Result': 'success',
                     'ExecMainStatus': '0', 'ExecMainExitTimestampMonotonic': '1000000'}

    def test_waits_for_live_work_then_returns_without_mutation(self):
        elapsed = [0]
        events = []
        def state(unit, timeout):
            return {**self.good, 'ActiveState': 'activating'} if elapsed[0] == 0 else self.good
        def sleep(seconds):
            elapsed[0] += seconds
        self.gate.wait_ready(state, sleep=sleep, clock=lambda: elapsed[0], report=events.append)
        self.assertEqual(elapsed[0], 60)
        self.assertIn('ready', events[-1])

    def test_terminal_failure_does_not_wait_or_retry(self):
        with self.assertRaises(RuntimeError), patch.object(self.gate.time, 'sleep') as sleep:
            self.gate.wait_ready(lambda unit, timeout: {**self.good, 'ActiveState': 'failed', 'Result': 'exit-code'})
        sleep.assert_not_called()

    def test_missing_and_never_run_units_fail_closed(self):
        for changes in [{'LoadState': 'not-found'}, {'ExecMainExitTimestampMonotonic': '0'}]:
            with self.subTest(changes=changes), self.assertRaises(RuntimeError):
                self.gate.wait_ready(lambda unit, timeout: {**self.good, **changes})

    def test_live_work_has_bounded_wait(self):
        elapsed = [0]
        def sleep(seconds):
            elapsed[0] += seconds
        with self.assertRaises(TimeoutError):
            self.gate.wait_ready(lambda unit, timeout: {**self.good, 'ActiveState': 'activating'},
                                 sleep=sleep, clock=lambda: elapsed[0], max_wait=120, report=lambda _: None)
        self.assertEqual(elapsed[0], 120)

    def test_query_errors_do_not_become_ready(self):
        def state(unit, timeout):
            raise OSError('query unavailable')
        with self.assertRaises(OSError):
            self.gate.wait_ready(state)

    def test_only_fixed_units_can_be_queried(self):
        with patch.object(self.gate.subprocess, 'run') as run, self.assertRaises(ValueError):
            self.gate.read_state('arbitrary.service')
        run.assert_not_called()

    def test_success_observed_after_deadline_is_not_accepted(self):
        elapsed = [0]
        events = []
        def state(unit, timeout):
            elapsed[0] = 121
            return self.good
        with self.assertRaises(TimeoutError):
            self.gate.wait_ready(state, clock=lambda: elapsed[0], max_wait=120, report=events.append)
        self.assertEqual(events, [])

    def test_query_timeout_is_limited_by_remaining_budget(self):
        elapsed = [0]
        timeouts = []
        def state(unit, timeout):
            timeouts.append(timeout)
            elapsed[0] += 9 if len(timeouts) == 1 else 1
            return self.good
        with self.assertRaises(TimeoutError):
            self.gate.wait_ready(state, clock=lambda: elapsed[0], max_wait=10, report=lambda _: None)
        self.assertEqual(timeouts, [10, 1])

    def test_failed_gitlab_export_invalidates_previous_marker(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            state = root / '.state'
            state.mkdir()
            marker = state / 'gitlab.success'
            marker.write_text('status=success\n')
            fail = root / 'native.sh'
            fail.write_text('#!/bin/sh\nexit 1\n')
            env = {**os.environ, 'BACKUP_STAGING_ROOT': str(root), 'BACKUP_STATUS_ROOT': str(state),
                   'GITLAB_BACKUP_SCRIPT': str(fail)}
            result = subprocess.run(['bash', str(ROOT / 'automation/backup-runner/run-vm100-scheduled.sh'),
                                     'gitlab'], env=env, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(marker.exists())


if __name__ == '__main__':
    unittest.main()
