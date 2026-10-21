#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source "$script_dir/restic-lib.sh"

inventory=${BACKUP_INVENTORY:?BACKUP_INVENTORY is required}
database=${1:?usage: upload-couchdb-stream.sh DATABASE RUN_ID RUN_DIR}
run_id=${2:?usage: upload-couchdb-stream.sh DATABASE RUN_ID RUN_DIR}
run_dir=${3:?usage: upload-couchdb-stream.sh DATABASE RUN_ID RUN_DIR}
stream_script=${BACKUP_COUCHDB_STREAM_SCRIPT:-$script_dir/stream-couchdb.py}
stream_dir="$run_dir/couchdb-stream"
metadata="$stream_dir/$database.metadata.json"
stream_hash="$stream_dir/$database.stream.sha256"
restic_output="$stream_dir/$database.restic.jsonl"
manifest="$stream_dir/$database.manifest.json"

mkdir -p "$stream_dir"
if [[ -n "${BACKUP_STREAM_RESTIC_REPOSITORY:-}" ]]; then
  export RESTIC_REPOSITORY="$BACKUP_STREAM_RESTIC_REPOSITORY"
else
  export RESTIC_REPOSITORY=$(restic_repo_for databases)
fi
export RESTIC_INTERACTIVE_STDIN=true

# The stream is never written to disk. tee computes a checksum in a side
# process while Restic receives the same bytes through the interactive Docker
# stdin path. A failed exporter or Restic command aborts the pipeline.
set -o pipefail
python3 "$stream_script" \
  --inventory "$inventory" \
  --database "$database" \
  --metadata-output "$metadata" \
  2>"$stream_dir/$database.export.log" \
  | tee >(sha256sum >"$stream_hash") \
  | restic_run backup --stdin \
      --stdin-filename "couchdb/$database.docs.ndjson.gz" \
      --tag "class=databases" \
      --tag "run_id=$run_id" \
      --tag "database=$database" \
      --json \
  >"$restic_output"

snapshot_id=$(python3 - "$restic_output" <<'PY'
import json
import re
import sys

snapshot = ''
for line in open(sys.argv[1], encoding='utf-8'):
    try:
        record = json.loads(line)
    except json.JSONDecodeError:
        continue
    if record.get('message_type') == 'summary':
        snapshot = record.get('snapshot_id') or ''
if not re.fullmatch(r'[0-9a-f]{64}', snapshot):
    raise SystemExit('stream Restic output has no valid snapshot id')
print(snapshot)
PY
)

stream_digest=$(awk '{print $1}' "$stream_hash")
[[ "$stream_digest" =~ ^[0-9a-f]{64}$ ]] || {
  echo 'stream checksum is missing or invalid' >&2
  exit 1
}

python3 - "$manifest" "$database" "$run_id" "$snapshot_id" "$stream_digest" "$metadata" <<'PY'
import json
import sys
from pathlib import Path

path, database, run_id, snapshot, digest, metadata = sys.argv[1:]
data = json.loads(Path(metadata).read_text(encoding='utf-8'))
Path(path).write_text(json.dumps({
    'schema_version': 1,
    'database': database,
    'run_id': run_id,
    'snapshot_id': snapshot,
    'stream_sha256': digest,
    'metadata': str(Path(metadata).relative_to(Path(path).parent.parent)),
    'doc_count': data.get('info', {}).get('doc_count'),
    'status': 'complete',
}, sort_keys=True) + '\n', encoding='utf-8')
PY

printf '%s\n' "$snapshot_id"
