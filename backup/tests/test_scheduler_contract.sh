#!/usr/bin/env bash
set -euo pipefail

root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
vm_runner="$root/automation/backup-runner/run-vm100-scheduled.sh"
pi_runner="$root/automation/backup-runner/pi-executor.sh"
pi_resource_runner="$root/automation/backup-runner/run-pi-capped.sh"
ssh_guard="$root/automation/backup-runner/pi-ssh-guard.sh"
service="$root/automation/backup-runner/systemd/homelab-backup@.service"
health_script="$root/backup/scripts/check-backup-health.sh"
health_service="$root/automation/backup-runner/systemd/homelab-backup-health.service"
health_timer="$root/automation/backup-runner/systemd/homelab-backup-health.timer"
weekly_timer="$root/automation/backup-runner/systemd/homelab-backup-verify-weekly.timer"

grep -q 'PI_BACKUP_SSH_TARGET' "$vm_runner"
grep -q 'run-class.sh.*gitlab' "$vm_runner"
grep -q 'run-class.sh.*database-instances' "$vm_runner"
grep -q 'run-instance-retention.sh' "$vm_runner"
grep -q 'run-retention.sh' "$vm_runner"
grep -q 'run_pi markers' "$vm_runner"
if grep -q 'run_pi retention' "$vm_runner"; then
  echo 'VM100 retention must not invoke Pi5 restic retention' >&2
  exit 1
fi
grep -q 'homelab-backup-executor' "$vm_runner"
grep -q 'SSH_ORIGINAL_COMMAND' "$ssh_guard"
grep -q 'accepts only the allow-listed' "$ssh_guard"
grep -q 'markers' "$ssh_guard"
grep -q 'simple-backup' "$root/docs/deployments/backup-scheduler-2026-10-06.md"
grep -q 'EnvironmentFile=/etc/homelab-backup/runner.env' "$service"
grep -q 'RCLONE_CONFIG_WORK_ROOT=/home/ubuntu/.homelab-backup-runtime' "$service"
grep -q 'SyslogIdentifier=homelab-backup-%i' "$service"
grep -q 'StandardOutput=journal' "$service"
grep -q 'TimeoutStartSec=12h' "$service"
grep -q 'ServerAliveInterval=30' "$vm_runner"
grep -q 'PI_BACKUP_COMMAND_TIMEOUT_SECONDS' "$vm_runner"
grep -q 'kill-after=60s' "$vm_runner"
grep -q 'cleanup-local-runs.sh' "$vm_runner"
grep -q 'check-backup-health.sh' "$health_service"
grep -q 'SyslogIdentifier=homelab-backup-health' "$health_service"
grep -q 'NoNewPrivileges=yes' "$health_service"
grep -q 'BACKUP_HEALTH_ACTIVE_MAX_AGE_SECONDS' "$health_script"
grep -q 'ExecMainStartTimestampMonotonic' "$health_script"
grep -q 'Pi backup health reported a dead-man marker problem' "$health_script"
test -x "$health_script"
test -x "$pi_resource_runner"
grep -q 'run-pi-capped.sh' "$pi_runner"
grep -q 'bounded Pi runner is missing' "$pi_runner"
grep -q 'run-pi-capped.sh' "$root/automation/ansible/playbooks/backup-health-repair.yml"
grep -q 'OnCalendar=.*12:00:00' "$health_timer"
grep -q 'OnCalendar=.*01:00:00' "$root/automation/backup-runner/systemd/homelab-backup-databases.timer"
grep -q 'OnCalendar=.*03:00:00' "$root/automation/backup-runner/systemd/homelab-backup-database-instances.timer"
grep -q 'OnCalendar=.*05:00:00' "$root/automation/backup-runner/systemd/homelab-backup-gitlab.timer"
grep -q 'OnCalendar=.*04:00:00' "$root/automation/backup-runner/systemd/homelab-backup-rustfs.timer"
grep -q 'OnCalendar=.*10:00:00' "$root/automation/backup-runner/systemd/homelab-backup-retention.timer"
grep -q 'OnCalendar=Sun .*09:00:00' "$weekly_timer"
grep -q 'homelab-backup-verify-weekly.service' "$weekly_timer"

echo 'scheduler contract tests passed'
