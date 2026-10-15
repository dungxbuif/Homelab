#!/usr/bin/env bash
set -euo pipefail

root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
vm_runner="$root/automation/backup-runner/run-vm100-scheduled.sh"
pi_runner="$root/automation/backup-runner/pi-executor.sh"
ssh_guard="$root/automation/backup-runner/pi-ssh-guard.sh"
service="$root/automation/backup-runner/systemd/homelab-backup@.service"

grep -q 'PI_BACKUP_SSH_TARGET' "$vm_runner"
grep -q 'run-class.sh.*gitlab' "$vm_runner"
grep -q 'run-retention.sh' "$pi_runner"
grep -q 'homelab-backup-executor' "$vm_runner"
grep -q 'SSH_ORIGINAL_COMMAND' "$ssh_guard"
grep -q 'accepts only the allow-listed' "$ssh_guard"
grep -q 'simple-backup' "$root/docs/deployments/backup-scheduler-2026-10-06.md"
grep -q 'EnvironmentFile=/etc/homelab-backup/runner.env' "$service"
grep -q 'OnCalendar=.*01:00:00' "$root/automation/backup-runner/systemd/homelab-backup-databases.timer"
grep -q 'OnCalendar=.*02:30:00' "$root/automation/backup-runner/systemd/homelab-backup-gitlab.timer"
grep -q 'OnCalendar=.*04:30:00' "$root/automation/backup-runner/systemd/homelab-backup-rustfs.timer"
grep -q 'OnCalendar=.*05:30:00' "$root/automation/backup-runner/systemd/homelab-backup-retention.timer"

echo 'scheduler contract tests passed'
