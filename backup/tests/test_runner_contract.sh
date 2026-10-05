#!/usr/bin/env bash
set -euo pipefail

root=$(cd -- "$(dirname -- "$0")/../.." && pwd)
runner="$root/automation/backup-runner/run-class.sh"
retention="$root/automation/backup-runner/run-retention.sh"

grep -q 'flock' "$runner"
grep -q 'run-database-backup.py' "$runner"
grep -q 'run-rustfs-backup.sh' "$runner"
grep -q 'upload-restic.sh' "$runner"
grep -q 'post-check-report.sh' "$runner"
grep -q 'verify-retention.sh' "$retention"
if grep -R -nE 'docker (service|stack) (stop|rm|down|scale)' "$root/automation/backup-runner"; then
  echo 'backup runner must not stop production services' >&2
  exit 1
fi
echo 'backup runner contract tests passed'
