import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/run_restic_container.py'
FAKE = ROOT / 'tests/fixtures/docker_lifecycle.py'


class ResticLifecycleTests(unittest.TestCase):
    def exercise(self, mode):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            docker = root / 'docker'
            docker.write_bytes(FAKE.read_bytes())
            docker.chmod(0o755)
            env = dict(os.environ, PATH=f'{root}:{os.environ["PATH"]}',
                       LIFECYCLE_FIXTURE=tmp, LIFECYCLE_MODE=mode)
            start = time.monotonic()
            command = ['python3', str(SCRIPT), '--timeout', '1s',
                                     '--grace', '0.1s', '--cleanup-timeout', '1s',
                                     '--', 'fixture-image', 'snapshots']
            if mode == 'cancel-launch':
                command = ['python3', '-c', '''
import importlib.util, os, pathlib, signal, sys
spec = importlib.util.spec_from_file_location("supervisor", sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
original = module.subprocess.Popen
first = True
def launching(*args, **kwargs):
    global first
    child = original(*args, **kwargs)
    if first:
        first = False
        pathlib.Path(os.environ["LIFECYCLE_FIXTURE"], "child-pid").write_text(str(child.pid))
        os.kill(os.getpid(), signal.SIGTERM)
    return child
module.subprocess.Popen = launching
sys.exit(module.run(["fixture-image"], 1, 0.1, 1))
''', str(SCRIPT)]
            result = subprocess.run(command,
                                    env=env, capture_output=True, text=True, timeout=8)
            if mode == 'cancel-launch':
                pid = int((root / 'child-pid').read_text())
                with self.assertRaises(ProcessLookupError):
                    os.kill(pid, 0)
            calls = [json.loads(line) for line in (root / 'calls').read_text().splitlines()] if (root / 'calls').exists() else []
            return result, calls, (root / 'active').exists(), time.monotonic() - start

    def test_success_preserves_json_and_verifies_no_container_left(self):
        result, calls, active, _ = self.exercise('success')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {'fixture': 'completed'})
        self.assertFalse(active)
        self.assertTrue(any(c[:2] == ['container', 'ls'] for c in calls))

    def test_term_resistant_client_is_killed_and_only_its_container_removed(self):
        result, calls, active, elapsed = self.exercise('hang')
        self.assertEqual(result.returncode, 124, result.stderr)
        self.assertLess(elapsed, 5)
        self.assertFalse(active)
        self.assertIn(['container', 'rm', '--force', 'a' * 64], calls)
        label = calls[0][calls[0].index('--label') + 1]
        queries = [c for c in calls if c[:2] == ['container', 'ls']]
        self.assertEqual(len(queries), 2)
        self.assertTrue(all('label=' + label in c for c in queries))

    def test_disconnected_client_retains_failure_after_cleanup(self):
        result, calls, active, _ = self.exercise('disconnect')
        self.assertEqual(result.returncode, 7, result.stderr)
        self.assertFalse(active)
        self.assertIn(['container', 'rm', '--force', 'a' * 64], calls)

    def test_cleanup_failure_is_explicit(self):
        result, _, active, _ = self.exercise('cleanup-failure')
        self.assertEqual(result.returncode, 125, result.stderr)
        self.assertTrue(active)
        self.assertIn('cleanup could not be verified', result.stderr)

    def test_late_create_is_not_mistaken_for_verified_cleanup(self):
        result, _, active, _ = self.exercise('late-create')
        self.assertEqual(result.returncode, 125, result.stderr)
        self.assertTrue(active)
        self.assertIn('creation outcome is unresolved', result.stderr)

    def test_cancellation_during_launch_records_and_reaps_child(self):
        result, calls, active, _ = self.exercise('cancel-launch')
        self.assertEqual(result.returncode, 125, result.stderr)
        self.assertFalse(active)
        self.assertFalse(any(c[0] == 'start' for c in calls))

    def test_opt_in_interactive_stdin_reaches_docker_start(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            docker = root / 'docker'
            docker.write_bytes(FAKE.read_bytes())
            docker.chmod(0o755)
            env = dict(os.environ, PATH=f'{root}:{os.environ["PATH"]}',
                       LIFECYCLE_FIXTURE=tmp, LIFECYCLE_MODE='success')
            command = ['python3', str(SCRIPT), '--timeout', '1s',
                       '--grace', '0.1s', '--cleanup-timeout', '1s',
                       '--interactive-stdin', '--', 'fixture-image', 'backup', '--stdin']
            result = subprocess.run(command, env=env, input=b'stream-payload',
                                    capture_output=True, timeout=8)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((root / 'stdin').read_bytes(), b'stream-payload')
            calls = [json.loads(line) for line in (root / 'calls').read_text().splitlines()]
            self.assertIn('--interactive', calls[0])
            self.assertIn('--interactive', calls[1])


if __name__ == '__main__':
    unittest.main()
