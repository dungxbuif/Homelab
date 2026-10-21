#!/usr/bin/env python3
import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class HealthReportingTests(unittest.TestCase):
    def run_health(self, start='12285000000', remote_code=0, active_class='retention',
                   uptime='12345.00 20000.00', lock_held=False, expected_classes='gitlab',
                   marker_class='gitlab'):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / '.state').mkdir()
            if marker_class:
                (root / f'.state/{marker_class}.success').write_text(
                    f'completed_at={int(time.time())}\n')
            (root / 'uptime').write_text(f'{uptime}\n')
            systemctl = root / 'systemctl'
            systemctl.write_text(f'''#!/bin/sh
case "$*" in
  is-failed*) echo inactive ;;
  *homelab-backup@{active_class}.service*ActiveState*) echo activating ;;
  *ActiveState*) echo inactive ;;
  *homelab-backup@{active_class}.service*ExecMainStartTimestampMonotonic*) printf '%s\\n' "$FAKE_STARTED_US" ;;
  *ExecMainStartTimestampMonotonic*) printf '\\n' ;;
esac
''')
            systemctl.chmod(0o700)
            if lock_held:
                flock = root / 'flock'
                flock.write_text('#!/bin/sh\nexit 1\n')
                flock.chmod(0o700)
            remote = root / 'remote.sh'
            remote.write_text(f'#!/bin/sh\necho "[backup-health] Pi marker probe"\nexit {remote_code}\n')
            env = {**os.environ, 'PATH': f'{root}:{os.environ["PATH"]}',
                   'BACKUP_STAGING_ROOT': str(root), 'BACKUP_HEALTH_EXPECTED_CLASSES': expected_classes,
                   'BACKUP_HEALTH_SKIP_LOCK': 'false' if lock_held else 'true',
                   'BACKUP_HEALTH_MIN_FREE_BYTES': '0',
                   'BACKUP_HEALTH_DISK_WARN_PERCENT': '100',
                   'BACKUP_HEALTH_DISK_FAIL_PERCENT': '101',
                   'BACKUP_HEALTH_UPTIME_FILE': str(root / 'uptime'), 'FAKE_STARTED_US': start,
                   'BACKUP_LOCK_FILE': str(root / 'backup.lock'),
                   'BACKUP_HEALTH_REMOTE_PI': 'true', 'BACKUP_HEALTH_REMOTE_SCRIPT': str(remote)}
            return subprocess.run(['bash', str(ROOT / 'backup/scripts/check-backup-health.sh')],
                                  env=env, capture_output=True, text=True, timeout=15)

    def test_in_limit_gitlab_run_is_healthy(self):
        result = self.run_health(start='4000000000', uptime='22000.00 20000.00',
                                 active_class='gitlab')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('state=running runtime=18000s', result.stdout)

    def test_overlong_gitlab_run_fails(self):
        result = self.run_health(start='3990000000', uptime='22000.00 20000.00',
                                 active_class='gitlab')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('overlong unit: homelab-backup@gitlab.service', result.stdout)

    def test_databases_historical_runtime_is_within_default_limit(self):
        result = self.run_health(start='16400000000', uptime='22000.00 20000.00',
                                 active_class='databases')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('runtime=5600s limit=7200s', result.stdout)

    def test_local_active_class_defers_missing_marker(self):
        result = self.run_health(active_class='database-instances', expected_classes='database-instances', marker_class='')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('database-instances.success=deferred_active', result.stdout)
        self.assertNotIn('missing success marker: database-instances', result.stdout)

    def test_configs_unit_is_checked_and_marker_is_reported(self):
        result = self.run_health(active_class='configs', expected_classes='configs', marker_class='configs')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('homelab-backup@configs.service', result.stdout)
        self.assertIn('configs.success_age=', result.stdout)

    def test_held_lock_without_backup_unit_fails(self):
        result = self.run_health(active_class='no-such-class', lock_held=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('backup lock is held without an active backup unit', result.stdout)

    def test_held_lock_with_remote_runner_is_healthy(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / '.state').mkdir()
            (root / '.state/gitlab.success').write_text(f'completed_at={int(time.time())}\n')
            (root / '.state/restore-drill.success').write_text(f'completed_at={int(time.time())}\n')
            (root / 'uptime').write_text('12345.00 20000.00\n')
            flock = root / 'flock'
            flock.write_text('#!/bin/sh\nexit 1\n')
            flock.chmod(0o700)
            pgrep = root / 'pgrep'
            pgrep.write_text('#!/bin/sh\nexit 0\n')
            pgrep.chmod(0o700)
            env = {**os.environ, 'PATH': f'{root}:{os.environ["PATH"]}',
                   'BACKUP_STAGING_ROOT': str(root), 'BACKUP_HEALTH_EXPECTED_CLASSES': 'gitlab',
                   'BACKUP_HEALTH_SKIP_LOCK': 'false', 'BACKUP_HEALTH_MIN_FREE_BYTES': '0',
                   'BACKUP_HEALTH_DISK_WARN_PERCENT': '100', 'BACKUP_HEALTH_DISK_FAIL_PERCENT': '101',
                   'BACKUP_HEALTH_UPTIME_FILE': str(root / 'uptime'),
                   'BACKUP_LOCK_FILE': str(root / 'backup.lock'),
                   'BACKUP_HEALTH_ACTIVE_PROCESS_PATTERN': 'run-retention'}
            result = subprocess.run(['bash', str(ROOT / 'backup/scripts/check-backup-health.sh')],
                                    env=env, capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('backup_lock=held_by_active_backup', result.stdout)

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

    def test_success_notification_is_opt_in(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / '.state').mkdir()
            (root / '.state/gitlab.success').write_text(f'completed_at={int(time.time())}\n')
            (root / '.state/restore-drill.success').write_text(f'completed_at={int(time.time())}\n')
            (root / 'uptime').write_text('12345.00 20000.00\n')
            notify = root / 'notify.sh'
            notify.write_text('#!/bin/sh\nprintf "%s\\n" "$*" > "$NOTIFY_OUTPUT"\n')
            notify.chmod(0o700)
            env = {**os.environ,
                   'BACKUP_STAGING_ROOT': str(root),
                   'BACKUP_HEALTH_EXPECTED_CLASSES': 'gitlab',
                   'BACKUP_HEALTH_SKIP_LOCK': 'true',
                   'BACKUP_HEALTH_MIN_FREE_BYTES': '0',
                   'BACKUP_HEALTH_DISK_WARN_PERCENT': '100',
                   'BACKUP_HEALTH_DISK_FAIL_PERCENT': '101',
                   'BACKUP_HEALTH_UPTIME_FILE': str(root / 'uptime'),
                   'BACKUP_HEALTH_NOTIFY_SUCCESS': 'true',
                   'BACKUP_NOTIFY_SCRIPT': str(notify),
                   'NOTIFY_OUTPUT': str(root / 'notification.txt')}
            result = subprocess.run(['bash', str(ROOT / 'backup/scripts/check-backup-health.sh'), '--notify'],
                                    env=env, capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('--status success', (root / 'notification.txt').read_text())
            self.assertIn('daily backup health passed', (root / 'notification.txt').read_text())

    def test_success_notification_is_silent_when_disabled(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / '.state').mkdir()
            (root / '.state/gitlab.success').write_text(f'completed_at={int(time.time())}\n')
            (root / '.state/restore-drill.success').write_text(f'completed_at={int(time.time())}\n')
            (root / 'uptime').write_text('12345.00 20000.00\n')
            notify = root / 'notify.sh'
            notify.write_text('#!/bin/sh\nprintf "%s\\n" "$*" > "$NOTIFY_OUTPUT"\n')
            notify.chmod(0o700)
            env = {**os.environ,
                   'BACKUP_STAGING_ROOT': str(root),
                   'BACKUP_HEALTH_EXPECTED_CLASSES': 'gitlab',
                   'BACKUP_HEALTH_SKIP_LOCK': 'true',
                   'BACKUP_HEALTH_MIN_FREE_BYTES': '0',
                   'BACKUP_HEALTH_DISK_WARN_PERCENT': '100',
                   'BACKUP_HEALTH_DISK_FAIL_PERCENT': '101',
                   'BACKUP_HEALTH_UPTIME_FILE': str(root / 'uptime'),
                   'BACKUP_HEALTH_NOTIFY_SUCCESS': 'false',
                   'BACKUP_NOTIFY_SCRIPT': str(notify),
                   'NOTIFY_OUTPUT': str(root / 'notification.txt')}
            result = subprocess.run(['bash', str(ROOT / 'backup/scripts/check-backup-health.sh'), '--notify'],
                                    env=env, capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertFalse((root / 'notification.txt').exists())

    def test_disk_usage_warning_threshold(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / '.state').mkdir()
            (root / '.state/gitlab.success').write_text(f'completed_at={int(time.time())}\n')
            (root / 'uptime').write_text('12345.00 20000.00\n')
            env = {**os.environ,
                   'BACKUP_STAGING_ROOT': str(root),
                   'BACKUP_HEALTH_EXPECTED_CLASSES': 'gitlab',
                   'BACKUP_HEALTH_SKIP_LOCK': 'true',
                   'BACKUP_HEALTH_MIN_FREE_BYTES': '0',
                   'BACKUP_HEALTH_DISK_WARN_PERCENT': '1',
                   'BACKUP_HEALTH_DISK_FAIL_PERCENT': '99',
                   'BACKUP_HEALTH_UPTIME_FILE': str(root / 'uptime')}
            result = subprocess.run(['bash', str(ROOT / 'backup/scripts/check-backup-health.sh')],
                                    env=env, capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('disk usage is', result.stdout)

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
