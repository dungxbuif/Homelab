#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=restic-lib.sh
source "$script_dir/restic-lib.sh"

class=${1:?usage: upload-restic.sh CLASS RUN_DIR [RUN_ID]}
run_dir=${2:?usage: upload-restic.sh CLASS RUN_DIR}
run_id=${3:-}
[[ -d "$run_dir" && -f "$run_dir/COMPLETE" && -f "$run_dir/manifest.json" ]] || {
  echo 'only a complete run with manifest can be uploaded' >&2
  exit 1
}
if [[ -z "$run_id" ]]; then
  run_id=$(python3 - "$run_dir/manifest.json" "$(basename "$run_dir")" <<'PY'
import json
import sys

manifest_path, fallback = sys.argv[1:]
with open(manifest_path, encoding="utf-8") as handle:
    manifest = json.load(handle)
print(manifest.get("run_id") or fallback)
PY
  )
fi
repo=$(restic_repo_for "$class")
export RESTIC_REPOSITORY="$repo"
export RESTIC_INPUT_DIR=$(cd -- "$run_dir" && pwd)

preflight_log="$run_dir/restic-preflight.log"
preflight_timeout=${RESTIC_PREFLIGHT_TIMEOUT:-10m}
if ! RESTIC_COMMAND_TIMEOUT="$preflight_timeout" restic_run snapshots >"$preflight_log" 2>&1; then
  if grep -Eiq 'RATE_LIMIT|rateLimitExceeded|quota|HTTP 429|too many requests' "$preflight_log"; then
    echo 'Restic repository preflight hit Google Drive API quota; use a project-owned OAuth client or retry after the bounded backoff' >&2
    exit 1
  fi
  if grep -Eiq 'already locked|unable to create lock in backend|lock was created at' "$preflight_log"; then
    if pgrep -x restic >/dev/null 2>&1 || pgrep -f 'docker run.*restic/restic' >/dev/null 2>&1; then
      echo 'Restic repository is locked while a local Restic process is active; refusing automatic unlock' >&2
      exit 1
    fi
    {
      printf '%s\n' 'Restic lock appears stale; no local Restic process is active, running native unlock.'
      RESTIC_COMMAND_TIMEOUT="$preflight_timeout" restic_run unlock &&
      RESTIC_COMMAND_TIMEOUT="$preflight_timeout" restic_run snapshots
    } >>"$preflight_log" 2>&1 || {
      echo "Restic stale-lock recovery failed; see $preflight_log" >&2
      exit 1
    }
  elif [[ "${RESTIC_ALLOW_INIT:-false}" != 'true' ]]; then
    echo "Restic repository preflight failed; refusing implicit init (see $preflight_log)" >&2
    exit 1
  else
    restic_run init >>"$preflight_log" 2>&1
  fi
fi
restic_run backup /backup-run --tag "class=$class" --tag "run_id=$run_id" --json \
  --exclude='**/.DS_Store' \
  --exclude='/backup-run/restic-backup.json' \
  --exclude='/backup-run/restic-preflight.log' \
  --exclude='/backup-run/restic-check.log' \
  --exclude='/backup-run/remote' \
  --host homelab-backup-runner \
  > "$run_dir/restic-backup.json"
check_log="$run_dir/restic-check.log"
if ! restic_run check --read-data-subset=1/10 >"$check_log" 2>&1; then
  if grep -Eiq 'already locked|unable to create lock in backend|lock was created at|repository is already locked' "$check_log" \
    && ! pgrep -x restic >/dev/null 2>&1 \
    && ! pgrep -f 'docker run.*restic/restic' >/dev/null 2>&1; then
    {
      printf '%s\n' 'Restic post-upload check found a stale repository lock; no local Restic process is active, unlocking once.'
      RESTIC_COMMAND_TIMEOUT="$preflight_timeout" restic_run unlock &&
      restic_run check --read-data-subset=1/10
    } >>"$check_log" 2>&1 || {
      echo "Restic post-upload check failed after stale-lock recovery; remote snapshot is not trusted (see $check_log)" >&2
      exit 1
    }
  else
    echo "Restic post-upload check failed; remote snapshot is not trusted (see $check_log)" >&2
    exit 1
  fi
fi

mkdir -p "$run_dir/remote"
restic_run snapshots --json --tag "run_id=$run_id" > "$run_dir/remote/snapshots.json"
snapshot_id=$(python3 -c 'import json,sys; data=json.load(open(sys.argv[1])); print(data[-1]["id"] if data else "")' "$run_dir/remote/snapshots.json")
[[ -n "$snapshot_id" ]] || { echo 'restic snapshot id not found' >&2; exit 1; }
printf '%s\n' "$snapshot_id" > "$run_dir/remote/snapshot-id"
printf '%s\n' "$run_id" > "$run_dir/remote/run-id"
printf '%s\n' "$snapshot_id"
