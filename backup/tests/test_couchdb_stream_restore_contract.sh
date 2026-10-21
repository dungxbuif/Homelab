#!/usr/bin/env bash
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
script="$root/backup/scripts/restore-couchdb-stream-snapshots.sh"
grep -q 'snapshots --no-lock --json' "$script"
grep -q 'stream_metadata=true' "$script"
grep -q 'restore-couchdb-stream.py' "$script"
grep -q 'restore target must be a new absolute directory' "$script"
echo 'CouchDB stream snapshot restore contract tests passed'
