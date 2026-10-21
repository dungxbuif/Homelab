#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
database=${1:?usage: restore-couchdb-stream-snapshots.sh DATABASE RUN_ID TARGET_DIR CONTAINER}
run_id=${2:?usage: restore-couchdb-stream-snapshots.sh DATABASE RUN_ID TARGET_DIR CONTAINER}
target=${3:?usage: restore-couchdb-stream-snapshots.sh DATABASE RUN_ID TARGET_DIR CONTAINER}
container=${4:?usage: restore-couchdb-stream-snapshots.sh DATABASE RUN_ID TARGET_DIR CONTAINER}

[[ "$database" =~ ^[a-z][a-z0-9_$()-]*$ ]] || { echo 'invalid database name' >&2; exit 2; }
[[ "$run_id" =~ ^[A-Za-z0-9._-]+$ ]] || { echo 'invalid run id' >&2; exit 2; }
[[ "$target" == /* && ! -e "$target" && ! -L "$target" ]] || {
  echo 'restore target must be a new absolute directory' >&2
  exit 2
}

# shellcheck source=restic-lib.sh
source "$script_dir/restic-lib.sh"
export RESTIC_REPOSITORY
RESTIC_REPOSITORY=$(restic_repo_for databases)
umask 077
mkdir -- "$target"
RESTIC_RESTORE_DIR=$(cd -- "$target" && pwd)
export RESTIC_RESTORE_DIR

snapshot_json=$(mktemp)
trap 'rm -f -- "$snapshot_json"' EXIT
restic_run snapshots --no-lock --json --tag "run_id=$run_id" >"$snapshot_json"

read -r stream_snapshot metadata_snapshot <<EOF
$(python3 - "$snapshot_json" "$database" "$run_id" <<'PY'
import json
import re
import sys

path, database, run_id = sys.argv[1:]
records = json.loads(open(path, encoding="utf-8").read())
stream = []
metadata = []
for record in records:
    tags = set(record.get("tags", []))
    if f"run_id={run_id}" not in tags or f"database={database}" not in tags:
        continue
    snapshot_id = record.get("id", "")
    if not re.fullmatch(r"[0-9a-f]{64}", snapshot_id):
        continue
    if "stream_metadata=true" in tags:
        metadata.append(snapshot_id)
    else:
        stream.append(snapshot_id)
if not stream or not metadata:
    raise SystemExit("matching stream and metadata snapshots were not found")
print(stream[-1], metadata[-1])
PY
)
EOF

restic_run restore "$metadata_snapshot" --no-lock --target /restore-target
restic_run restore "$stream_snapshot" --no-lock --target /restore-target

metadata_file=$(find "$target" -type f -name "$database.metadata.json" -print -quit)
stream_file=$(find "$target" -type f -name "$database.docs.ndjson.gz" -print -quit)
[[ -n "$metadata_file" && -n "$stream_file" ]] || {
  echo 'restored stream or metadata file is missing' >&2
  exit 1
}

python3 "$script_dir/restore-couchdb-stream.py" \
  --stream "$stream_file" \
  --metadata "$metadata_file" \
  --target "$database" \
  --container "$container"
