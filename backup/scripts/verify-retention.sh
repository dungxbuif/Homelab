#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=restic-lib.sh
source "$script_dir/restic-lib.sh"

class=${1:?usage: verify-retention.sh CLASS}
repo=$(restic_repo_for "$class")
export RESTIC_REPOSITORY="$repo"

# Never prune if repository integrity cannot be checked first.
restic_run check
restic_run forget --keep-daily 14 --keep-weekly 8 --keep-monthly 12 --prune
if [[ -n "${RESTIC_READ_DATA_SUBSET:-}" ]]; then
  restic_run check --read-data-subset="$RESTIC_READ_DATA_SUBSET"
fi
