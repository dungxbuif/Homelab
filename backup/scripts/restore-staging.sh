#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
class=${1:?usage: restore-staging.sh CLASS SNAPSHOT_ID TARGET_DIR}
snapshot_id=${2:?usage: restore-staging.sh CLASS SNAPSHOT_ID TARGET_DIR}
target=${3:?usage: restore-staging.sh CLASS SNAPSHOT_ID TARGET_DIR}
[[ $# == 3 && "$snapshot_id" =~ ^[a-f0-9]{64}$ && "$target" == /* ]] || {
  echo 'restore requires one exact snapshot ID and an absolute new target directory' >&2
  exit 2
}
case "$class" in
  databases|database-instances|rustfs|gitlab|configs) ;;
  *) echo 'unsupported backup class' >&2; exit 2 ;;
esac
[[ ! -e "$target" && ! -L "$target" ]] || {
  echo 'restore target must not already exist' >&2
  exit 2
}
# shellcheck source=restic-lib.sh
source "$script_dir/restic-lib.sh"
repo=$(restic_repo_for "$class")
export RESTIC_REPOSITORY="$repo"
umask 077
# Exclusive creation also rejects a target created after the preflight check.
mkdir -- "$target"
RESTIC_RESTORE_DIR=$(cd -- "$target" && pwd)
export RESTIC_RESTORE_DIR
restic_run restore "$snapshot_id" --no-lock --target /restore-target
