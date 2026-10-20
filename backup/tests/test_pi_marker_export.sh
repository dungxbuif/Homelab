#!/usr/bin/env bash
set -euo pipefail

root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
executor="$root/automation/backup-runner/pi-executor.sh"
tmp=$(mktemp -d)
trap 'rm -rf -- "$tmp"' EXIT

mkdir -p "$tmp/state" "$tmp/app"
cat >"$tmp/env" <<EOF
BACKUP_STATUS_ROOT=$tmp/state
BACKUP_APP_ROOT=$tmp/app
EOF
cat >"$tmp/state/databases.success" <<'EOF'
run_id=databases-test
completed_at=1700000000
snapshot_id=snapshot-databases
EOF
cat >"$tmp/state/rustfs.success" <<'EOF'
run_id=rustfs-test
completed_at=1700000001
snapshot_id=snapshot-rustfs
EOF

output=$(BACKUP_ENV_FILE="$tmp/env" bash "$executor" markers)
grep -q '^MARKER databases$' <<<"$output"
grep -q '^snapshot_id=snapshot-databases$' <<<"$output"
grep -q '^MARKER rustfs$' <<<"$output"
grep -q '^snapshot_id=snapshot-rustfs$' <<<"$output"
test "$(grep -c '^ENDMARKER$' <<<"$output")" -eq 2

echo 'Pi marker export tests passed'
