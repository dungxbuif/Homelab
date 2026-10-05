#!/usr/bin/env bash
set -euo pipefail

root=$(cd -- "$(dirname -- "$0")/../.." && pwd)
grep -q 'restic_run check' "$root/backup/scripts/verify-retention.sh"
grep -q 'keep-daily 14' "$root/backup/scripts/verify-retention.sh"
grep -q 'only a complete run' "$root/backup/scripts/upload-restic.sh"
grep -q 'RCLONE_CONFIG_WORKDIR' "$root/backup/scripts/restic-lib.sh"
grep -q 'cp "\$RCLONE_CONFIG_FILE"' "$root/backup/scripts/restic-lib.sh"
if grep -q 'RCLONE_CONFIG_FILE:/config/rclone.conf:ro' "$root/backup/scripts/restic-lib.sh"; then
  echo 'rclone config must be writable inside the upload working copy' >&2
  exit 1
fi
if grep -R -n 'rclone sync.*--delete' "$root/backup/scripts"; then
  echo 'destructive rclone sync is forbidden' >&2
  exit 1
fi
echo 'restic contract tests passed'
