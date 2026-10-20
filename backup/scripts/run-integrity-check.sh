#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=restic-lib.sh
source "$script_dir/restic-lib.sh"

class=${1:?usage: run-integrity-check.sh CLASS}
case "$class" in
  databases|database-instances|rustfs|gitlab|configs) ;;
  *) echo "unsupported backup class: $class" >&2; exit 2 ;;
esac

subset=${RESTIC_READ_DATA_SUBSET:-1/10}
export RESTIC_REPOSITORY=$(restic_repo_for "$class")
echo "deep integrity check: class=$class subset=$subset" >&2
restic_run check --read-data-subset="$subset"
