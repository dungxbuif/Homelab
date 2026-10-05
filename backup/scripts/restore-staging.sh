#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=restic-lib.sh
source "$script_dir/restic-lib.sh"

class=${1:?usage: restore-staging.sh CLASS SNAPSHOT_ID TARGET_DIR}
snapshot_id=${2:?usage: restore-staging.sh CLASS SNAPSHOT_ID TARGET_DIR}
target=${3:?usage: restore-staging.sh CLASS SNAPSHOT_ID TARGET_DIR}
repo=$(restic_repo_for "$class")
export RESTIC_REPOSITORY="$repo"
mkdir -p "$target"
export RESTIC_RESTORE_DIR=$(cd -- "$target" && pwd)
restic_run restore "$snapshot_id" --target /restore-target
