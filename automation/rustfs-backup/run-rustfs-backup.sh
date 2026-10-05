#!/usr/bin/env bash
set -euo pipefail

staging_root=${1:?usage: run-rustfs-backup.sh STAGING_ROOT RUN_ID INVENTORY CREDENTIALS_FILE}
run_id=${2:?usage: run-rustfs-backup.sh STAGING_ROOT RUN_ID INVENTORY CREDENTIALS_FILE}
inventory=${3:?usage: run-rustfs-backup.sh STAGING_ROOT RUN_ID INVENTORY CREDENTIALS_FILE}
credentials=${4:?usage: run-rustfs-backup.sh STAGING_ROOT RUN_ID INVENTORY CREDENTIALS_FILE}
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
final="$staging_root/$run_id"
tmp="$staging_root/.$run_id.incomplete"
[[ ! -e "$final" && ! -e "$tmp" ]] || { echo "run already exists: $run_id" >&2; exit 1; }
mkdir -p "$tmp"

python3 "$script_dir/export-buckets.py" \
  --inventory "$inventory" \
  --credentials-file "$credentials" \
  --output "$tmp"

python3 - "$tmp/rustfs-adapter.json" "$tmp/manifest.json" "$run_id" <<'PY'
import json
import sys
from pathlib import Path

adapter_path, manifest_path, run_id = map(Path, sys.argv[1:])
adapter = json.loads(adapter_path.read_text(encoding="utf-8"))
manifest = {
    "schema_version": 1,
    "kind": "rustfs",
    "status": "complete",
    "run_id": str(run_id),
    "coverage": [bucket["bucket"] for bucket in adapter["buckets"]],
    "bucket_count": len(adapter["buckets"]),
    "excluded_retired": adapter.get("excluded_retired", []),
    "restore_contract": "restore selected bucket into an isolated S3 bucket and compare object key, size, and exported file hash",
}
manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY

(
  cd "$tmp"
  find . -type f ! -name manifest.json ! -name checksums.sha256 ! -name COMPLETE -print0 \
    | sort -z \
    | xargs -0 sha256sum > checksums.sha256
)
printf '%s\n' "$run_id" > "$tmp/COMPLETE"
mv "$tmp" "$final"
printf '%s\n' "$final"
