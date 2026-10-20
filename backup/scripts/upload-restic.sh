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
preflight_mode=${RESTIC_PREFLIGHT_MODE:-config}
if [[ "$preflight_mode" == snapshots ]]; then
  preflight_command=(snapshots)
elif [[ "$preflight_mode" == config ]]; then
  preflight_command=(cat config)
else
  echo 'RESTIC_PREFLIGHT_MODE must be config or snapshots' >&2
  exit 2
fi
if ! RESTIC_COMMAND_TIMEOUT="$preflight_timeout" restic_run "${preflight_command[@]}" >"$preflight_log" 2>&1; then
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
run_structural_check() {
  if [[ -n "${RESTIC_READ_DATA_SUBSET:-}" ]]; then
    restic_run check "--read-data-subset=${RESTIC_READ_DATA_SUBSET}"
  else
    restic_run check
  fi
}
post_upload_check=${RESTIC_POST_UPLOAD_CHECK:-snapshot}
case "$post_upload_check" in
  snapshot)
    # Drive repositories can have a large index fan-out. Check snapshot
    # metadata immediately; full structural verification belongs to retention
    # and deep-verify so one upload cannot monopolize the global lock.
    printf '%s\n' 'structural restic check deferred to retention/deep-verify' >"$check_log"
    ;;
  structural)
    if ! run_structural_check >"$check_log" 2>&1; then
      if grep -Eiq 'already locked|unable to create lock in backend|lock was created at|repository is already locked' "$check_log" \
        && ! pgrep -x restic >/dev/null 2>&1 \
        && ! pgrep -f 'docker run.*restic/restic' >/dev/null 2>&1; then
        {
          printf '%s\n' 'Restic post-upload check found a stale repository lock; no local Restic process is active, unlocking once.'
          RESTIC_COMMAND_TIMEOUT="$preflight_timeout" restic_run unlock &&
          run_structural_check
        } >>"$check_log" 2>&1 || {
          echo "Restic post-upload check failed after stale-lock recovery; remote snapshot is not trusted (see $check_log)" >&2
          exit 1
        }
      else
        echo "Restic post-upload check failed; remote snapshot is not trusted (see $check_log)" >&2
        exit 1
      fi
    fi
    ;;
  *)
    echo 'RESTIC_POST_UPLOAD_CHECK must be snapshot or structural' >&2
    exit 2
    ;;
esac

mkdir -p "$run_dir/remote"
snapshot_id=$(python3 - "$run_dir/restic-backup.json" <<'PY'
import json
import sys

snapshot_id = ''
with open(sys.argv[1], encoding='utf-8') as stream:
    for line in stream:
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if record.get('message_type') == 'summary':
            snapshot_id = record.get('snapshot_id') or ''
if not snapshot_id:
    raise SystemExit('restic backup summary did not contain snapshot_id')
print(snapshot_id)
PY
)
if [[ "${RESTIC_VERIFY_SNAPSHOT_METADATA:-false}" == true ]]; then
  restic_run snapshots --no-lock --json --tag "run_id=$run_id" > "$run_dir/remote/snapshots.json"
fi
[[ -n "$snapshot_id" ]] || { echo 'restic snapshot id not found' >&2; exit 1; }
printf '%s\n' "$snapshot_id" > "$run_dir/remote/snapshot-id"
printf '%s\n' "$run_id" > "$run_dir/remote/run-id"
printf '%s\n' "$snapshot_id"
