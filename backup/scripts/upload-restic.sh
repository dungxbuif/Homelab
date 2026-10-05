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

if ! restic_run snapshots >/dev/null 2>&1; then
  restic_run init >/dev/null
fi
restic_run backup /backup-run --tag "class=$class" --tag "run_id=$run_id" --json \
  --exclude='**/.DS_Store' \
  --host homelab-backup-runner \
  > "$run_dir/restic-backup.json"
restic_run check --read-data-subset=1/10 >/dev/null

mkdir -p "$run_dir/remote"
restic_run snapshots --json --tag "run_id=$run_id" > "$run_dir/remote/snapshots.json"
snapshot_id=$(python3 -c 'import json,sys; data=json.load(open(sys.argv[1])); print(data[-1]["id"] if data else "")' "$run_dir/remote/snapshots.json")
[[ -n "$snapshot_id" ]] || { echo 'restic snapshot id not found' >&2; exit 1; }
printf '%s\n' "$snapshot_id" > "$run_dir/remote/snapshot-id"
printf '%s\n' "$snapshot_id"
