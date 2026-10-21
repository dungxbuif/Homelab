#!/usr/bin/env bash
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
grep -q 'RESTIC_INTERACTIVE_STDIN' "$root/backup/scripts/restic-lib.sh"
grep -q -- '--interactive-stdin' "$root/backup/scripts/restic-lib.sh"
grep -q -- '--stdin-filename' "$root/backup/scripts/upload-couchdb-stream.sh"
grep -q 'stream_sha256' "$root/backup/scripts/upload-couchdb-stream.sh"
grep -q 'status.*complete' "$root/backup/scripts/upload-couchdb-stream.sh"
grep -q 'BACKUP_STREAM_RESTIC_REPOSITORY' "$root/backup/scripts/upload-couchdb-stream.sh"
grep -q 'RESTIC_LOCAL_REPOSITORY_DIR' "$root/backup/scripts/restic-lib.sh"
echo 'CouchDB stream Restic contract tests passed'
