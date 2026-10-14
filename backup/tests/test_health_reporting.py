#!/usr/bin/env python3
import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class HealthReportingTests(unittest.TestCase):
    def run_health(self, start='12285000000', remote_code=0):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / '.state').mkdir()
            (root / '.state/gitlab.success').write_text(f'completed_at={int(time.time())}\n')
            (root / 'uptime').write_text('12345.00 20000.00\n')
            systemctl = root / 'systemctl'
            systemctl.write_text('''#!/bin/sh
case "$*" in
  is-failed*) echo inactive ;;
  *retention.service*ActiveState*) echo activating ;;
  *ActiveState*) echo inactive ;;
  *ExecMainStartTimestampMonotonic*) printf '%s\\n' "$FAKE_STARTED_US" ;;
esac
''')
            systemctl.chmod(0o700)
            remote = root / 'remote.sh'
            remote.write_text(f'#!/bin/sh\necho "[backup-health] Pi marker probe"\nexit {remote_code}\n')
            env = {**os.environ, 'PATH': f'{root}:{os.environ["PATH"]}',
                   'BACKUP_STAGING_ROOT': str(root), 'BACKUP_HEALTH_EXPECTED_CLASSES': 'gitlab',
                   'BACKUP_HEALTH_SKIP_LOCK': 'true', 'BACKUP_HEALTH_MIN_FREE_BYTES': '0',
                   'BACKUP_HEALTH_UPTIME_FILE': str(root / 'uptime'), 'FAKE_STARTED_US': start,
                   'BACKUP_HEALTH_REMOTE_PI': 'true', 'BACKUP_HEALTH_REMOTE_SCRIPT': str(remote)}
            return subprocess.run(['bash', str(ROOT / 'backup/scripts/check-backup-health.sh')],
                                  env=env, capture_output=True, text=True, timeout=15)

    def test_activating_oneshot_uses_process_monotonic_start(self):
        result = self.run_health()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('runtime=60s', result.stdout)
        self.assertIn('Pi marker probe', result.stdout)
        self.assertNotIn('missing success marker: databases', result.stdout)

    def test_unknown_start_is_reported_not_treated_as_success(self):
        result = self.run_health(start='0')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('monotonic', result.stdout)

    def test_remote_failure_cannot_report_healthy(self):
        result = self.run_health(remote_code=1)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Pi backup health check failed', result.stdout)

    def test_ssh_guard_allows_only_exact_health_command(self):
        with tempfile.TemporaryDirectory() as directory:
            executor = Path(directory) / 'executor'
            executor.write_text('#!/bin/sh\nprintf "action=%s\\n" "$1"\n')
            executor.chmod(0o700)
            env = {**os.environ, 'BACKUP_PI_EXECUTOR': str(executor)}
            guard = str(ROOT / 'automation/backup-runner/pi-ssh-guard.sh')
            good = subprocess.run(['bash', guard], env={**env, 'SSH_ORIGINAL_COMMAND': f'{executor} health'},
                                  capture_output=True, text=True)
            self.assertEqual(good.returncode, 0, good.stderr)
            self.assertEqual(good.stdout.strip(), 'action=health')
            for suffix in ['health extra', 'health; id', 'shell']:
                bad = subprocess.run(['bash', guard], env={**env, 'SSH_ORIGINAL_COMMAND': f'{executor} {suffix}'},
                                     capture_output=True, text=True)
                self.assertEqual(bad.returncode, 2)

    def test_pi_health_checks_local_markers_without_recursion(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'backup/scripts').mkdir(parents=True)
            (root / 'runner.env').write_text('')
            (root / 'backup/scripts/check-backup-health.sh').write_text(
                'printf "%s|%s|%s\\n" "$BACKUP_HEALTH_EXPECTED_CLASSES" "$BACKUP_HEALTH_CHECK_UNITS" "$BACKUP_HEALTH_REMOTE_PI"\n')
            env = {**os.environ, 'BACKUP_APP_ROOT': str(root), 'BACKUP_ENV_FILE': str(root / 'runner.env')}
            result = subprocess.run(['bash', str(ROOT / 'automation/backup-runner/pi-executor.sh'), 'health'],
                                    env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), 'databases rustfs|false|false')


if __name__ == '__main__':
    unittest.main()
