#!/usr/bin/env bash
set -euo pipefail

root=$(cd -- "$(dirname -- "$0")/../.." && pwd)
grep -q 'restic_run check' "$root/backup/scripts/verify-retention.sh"
grep -q 'keep-daily 14' "$root/backup/scripts/verify-retention.sh"
grep -q 'only a complete run' "$root/backup/scripts/upload-restic.sh"
grep -q 'RESTIC_ALLOW_INIT' "$root/backup/scripts/upload-restic.sh"
grep -q 'restic/restic@sha256:' "$root/backup/scripts/restic-lib.sh"
grep -q 'database-instances' "$root/backup/scripts/restic-lib.sh"
grep -q 'RCLONE_DRIVE_PACER_MIN_SLEEP' "$root/backup/scripts/restic-lib.sh"
grep -q 'RCLONE_DRIVE_CHUNK_SIZE' "$root/backup/scripts/restic-lib.sh"
grep -q 'RCLONE_RETRIES_SLEEP:-30s' "$root/backup/scripts/restic-lib.sh"
grep -q 'RESTIC_COMMAND_TIMEOUT:-4h' "$root/backup/scripts/restic-lib.sh"
grep -q 'RCLONE_CONFIG_WORKDIR' "$root/backup/scripts/restic-lib.sh"
grep -q 'RCLONE_CONFIG_WORK_ROOT' "$root/backup/scripts/restic-lib.sh"
grep -q 'BACKUP_STAGING_ROOT/.runtime/rclone' "$root/backup/scripts/restic-lib.sh"
grep -q 'prepare_rclone_workdir.py' "$root/backup/scripts/restic-lib.sh"
if grep -q 'RCLONE_CONFIG_FILE:/config/rclone.conf:ro' "$root/backup/scripts/restic-lib.sh"; then
  echo 'rclone config must be writable inside the upload working copy' >&2
  exit 1
fi
grep -q 'restic-preflight.log' "$root/backup/scripts/upload-restic.sh"
grep -q 'RESTIC_PREFLIGHT_TIMEOUT:-10m' "$root/backup/scripts/upload-restic.sh"
grep -q 'Google Drive API quota' "$root/backup/scripts/upload-restic.sh"
grep -q 'restic-check.log' "$root/backup/scripts/upload-restic.sh"
grep -q 'already locked' "$root/backup/scripts/upload-restic.sh"
grep -q 'pgrep -x restic' "$root/backup/scripts/upload-restic.sh"
grep -q 'restic_run unlock' "$root/backup/scripts/upload-restic.sh"
if grep -R -n 'rclone sync.*--delete' "$root/backup/scripts"; then
  echo 'destructive rclone sync is forbidden' >&2
  exit 1
fi
echo 'restic contract tests passed'
