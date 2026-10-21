#!/usr/bin/env bash
set -euo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

printf 'backup-test\n' > "$tmp/artifact.bin"
(cd "$tmp" && sha256sum artifact.bin > checksums.sha256)
printf '%s\n' '{"status":"complete","kind":"databases","remote_snapshot_id":"snap-test","coverage":["postgresql/test"]}' > "$tmp/manifest.json"
touch "$tmp/COMPLETE"

output=$(
  "$root/scripts/post-check-report.sh" \
    --kind databases \
    --run-dir "$tmp" \
    --summary 'database post-check passed' \
    --run-id test-run \
    --dry-run
)

grep -q '"type": "hook"' <<<"$output"
grep -q 'PostgreSQL + CouchDB' <<<"$output"
grep -q 'Đã lưu và kiểm tra bản backup thành công' <<<"$output"
if grep -q 'Snapshot:' <<<"$output"; then
  echo 'success notification should not expose snapshot details' >&2
  exit 1
fi

rm "$tmp/COMPLETE"
if "$root/scripts/post-check-report.sh" \
  --kind databases \
  --run-dir "$tmp" \
  --summary 'should fail' \
  --dry-run >/dev/null 2>&1; then
  echo 'expected post-check failure' >&2
  exit 1
fi

echo 'post-check reporter tests passed'
