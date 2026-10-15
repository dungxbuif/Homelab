#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
app_root=${BACKUP_APP_ROOT:-$(cd -- "$script_dir/../.." && pwd)}
backup_scripts=${BACKUP_SCRIPTS_DIR:-$app_root/backup/scripts}
staging_root=${BACKUP_STAGING_ROOT:-/opt/apps/homelab-backup/runs}
status_root=${BACKUP_STATUS_ROOT:-$staging_root/.state}
max_age=${BACKUP_RETENTION_MAX_AGE_SECONDS:-93600}
lock_file=${BACKUP_LOCK_FILE:-/run/lock/homelab-backup.lock}

: "${RESTIC_PASSWORD_FILE:?RESTIC_PASSWORD_FILE is required}"
: "${RCLONE_CONFIG_FILE:?RCLONE_CONFIG_FILE is required}"
: "${BACKUP_LOCAL_RCLONE_BIN:?BACKUP_LOCAL_RCLONE_BIN is required}"
: "${RCLONE_REMOTE:?RCLONE_REMOTE is required}"
: "${DRIVE_ROOT:?DRIVE_ROOT is required}"

class=database-instances
marker="$status_root/$class.success"
[[ -f "$marker" ]] || { echo "retention blocked: no recent successful $class backup" >&2; exit 1; }
completed_at=$(sed -n 's/^completed_at=//p' "$marker")
[[ "$completed_at" =~ ^[0-9]+$ ]] || { echo "retention blocked: invalid $class success marker" >&2; exit 1; }
now=$(date -u +%s)
age=$((now - completed_at))
(( age >= 0 && age <= max_age )) || { echo "retention blocked: $class success marker is stale" >&2; exit 1; }

mkdir -p "$(dirname -- "$lock_file")"
exec 9>"$lock_file"
if ! flock -n 9; then
  echo 'another VM100 backup job holds the global lock' >&2
  exit 75
fi

bash "$backup_scripts/verify-retention.sh" "$class"
BACKUP_STAGING_ROOT="$staging_root" bash "$backup_scripts/cleanup-local-runs.sh" "$class"
