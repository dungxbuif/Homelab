#!/usr/bin/env bash
set -euo pipefail

root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
script="$root/automation/backup-runner/run-restore-drill.sh"
service="$root/automation/backup-runner/systemd/homelab-backup-restore-drill.service"
timer="$root/automation/backup-runner/systemd/homelab-backup-restore-drill.timer"
health="$root/backup/scripts/check-backup-health.sh"

bash -n "$script" "$health"
grep -q 'flock -n 9' "$script"
grep -q 'restore-staging.sh' "$script"
grep -q 'RESTIC_CONTAINER_USER' "$script"
grep -q 'sha256sum --quiet -c' "$script"
grep -q 'rm -rf -- "$run_dir"' "$script"
grep -q 'RCLONE_CONFIG_WORKDIR_CREATED' "$script"
grep -q 'restore-drill.success' "$script"
grep -q -- '--kind restore-drill' "$script"
grep -q 'PrivateTmp=yes' "$service"
grep -q 'ReadWritePaths=/opt/apps/homelab-backup /run/lock /tmp' "$service"
grep -q 'run-restore-drill.sh' "$service"
grep -q 'OnCalendar=\*-\*-01 14:00:00 Asia/Ho_Chi_Minh' "$timer"
grep -q 'restore_drill_max_age' "$health"

echo 'restore drill contract tests passed'
