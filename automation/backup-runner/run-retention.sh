#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
app_root=${BACKUP_APP_ROOT:-$(cd -- "$script_dir/../.." && pwd)}
backup_scripts=${BACKUP_SCRIPTS_DIR:-$app_root/backup/scripts}
staging_root=${BACKUP_STAGING_ROOT:-/ssd-data/infra/backups/homelab}
status_root=${BACKUP_STATUS_ROOT:-$staging_root/.state}
max_age=${BACKUP_RETENTION_MAX_AGE_SECONDS:-93600}
lock_file=${BACKUP_LOCK_FILE:-/run/lock/homelab-backup.lock}

: "${RESTIC_PASSWORD_FILE:?RESTIC_PASSWORD_FILE is required}"
: "${RCLONE_CONFIG_FILE:?RCLONE_CONFIG_FILE is required}"
: "${BACKUP_LOCAL_RCLONE_BIN:?BACKUP_LOCAL_RCLONE_BIN is required}"
: "${RCLONE_REMOTE:?RCLONE_REMOTE is required}"
: "${DRIVE_ROOT:?DRIVE_ROOT is required}"

mkdir -p "$(dirname -- "$lock_file")"
exec 9>"$lock_file"
if ! flock -n 9; then
  echo 'another homelab backup job holds the global lock' >&2
  exit 75
fi

# Retention is destructive. Require a recent post-check success for every
# class; run-class removes that marker before starting a new attempt.
now=$(date -u +%s)
for class in databases rustfs gitlab; do
  marker="$status_root/$class.success"
  [[ -f "$marker" ]] || {
    echo "retention blocked: no recent successful $class backup" >&2
    exit 1
  }
  completed_at=$(sed -n 's/^completed_at=//p' "$marker")
  [[ "$completed_at" =~ ^[0-9]+$ ]] || {
    echo "retention blocked: invalid $class success marker" >&2
    exit 1
  }
  age=$((now - completed_at))
  (( age >= 0 && age <= max_age )) || {
    echo "retention blocked: $class success marker is stale" >&2
    exit 1
  }
done

for class in databases rustfs gitlab; do
  bash "$backup_scripts/verify-retention.sh" "$class"
done

# Only clean local staging after every remote repository has passed its
# integrity check and prune. Pi5 has no GitLab staging directory, so that class
# is simply a no-op here; VM100 cleans its GitLab runs after this succeeds.
cleanup_local=${BACKUP_LOCAL_CLEANUP_SCRIPT:-$backup_scripts/cleanup-local-runs.sh}
for class in databases rustfs gitlab; do
  bash "$cleanup_local" "$class"
done
