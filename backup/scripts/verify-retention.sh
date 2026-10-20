#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=restic-lib.sh
source "$script_dir/restic-lib.sh"

class=${1:?usage: verify-retention.sh CLASS}
repo=$(restic_repo_for "$class")
export RESTIC_REPOSITORY="$repo"

# Never prune if repository integrity cannot be checked first. A previous
# interrupted run may leave a Restic lock behind; unlock only when no local
# Restic/rclone process is alive, then retry the read-only check once.
check_log=$(mktemp "${TMPDIR:-/tmp}/homelab-retention-check.XXXXXX")
cleanup_check_log() { rm -f -- "$check_log"; }
trap cleanup_check_log EXIT
if ! restic_run check >"$check_log" 2>&1; then
  if grep -Eiq 'already locked|unable to create lock in backend|lock was created at|repository is already locked' "$check_log" \
    && ! pgrep -x restic >/dev/null 2>&1 \
    && ! pgrep -x rclone >/dev/null 2>&1 \
    && ! pgrep -f 'docker run.*restic/restic' >/dev/null 2>&1; then
    cat "$check_log" >&2
    echo 'stale Restic lock detected with no local Restic/rclone process; unlocking once' >&2
    restic_run unlock
    restic_run check
  else
    cat "$check_log" >&2
    exit 1
  fi
fi
restic_run forget --keep-daily 14 --keep-weekly 8 --keep-monthly 12 --prune
if [[ -n "${RESTIC_READ_DATA_SUBSET:-}" ]]; then
  restic_run check --read-data-subset="$RESTIC_READ_DATA_SUBSET"
fi
