#!/usr/bin/env bash
set -euo pipefail

root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
runner="$root/automation/backup-runner/run-pi-capped.sh"

test -x "$runner"

tmp=$(mktemp -d)
trap 'rm -rf -- "$tmp"' EXIT

cat >"$tmp/record" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >"$PI_RESOURCE_TEST_RECORD"
EOF
chmod 0755 "$tmp/record"

cat >"$tmp/nice" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
[[ "$1" == '-n' ]] || exit 2
shift 2
exec "$@"
EOF
cat >"$tmp/ionice" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
[[ "$1" == '-c' ]] || exit 2
shift 2
[[ "$1" == '--' ]] || exit 2
shift
exec "$@"
EOF
chmod 0755 "$tmp/nice" "$tmp/ionice"

PATH="$tmp:$PATH" \
PI_RESOURCE_TEST_RECORD="$tmp/portable" \
  BACKUP_PI_RESOURCE_MODE=portable \
  BACKUP_PI_NICE=12 \
  BACKUP_PI_IONICE_CLASS=3 \
  bash "$runner" "$tmp/record" payload
grep -q -- 'payload' "$tmp/portable"

cat >"$tmp/systemd-run" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >"$PI_RESOURCE_TEST_RECORD"
exit 0
EOF
chmod 0755 "$tmp/systemd-run"

PATH="$tmp:$PATH" \
PI_RESOURCE_TEST_RECORD="$tmp/systemd" \
  BACKUP_PI_RESOURCE_MODE=systemd \
  BACKUP_PI_CPU_QUOTA=100% \
  BACKUP_PI_MEMORY_MAX=1G \
  BACKUP_PI_IO_WEIGHT=50 \
  bash "$runner" "$tmp/record" payload
grep -q -- '--scope' "$tmp/systemd"
grep -q -- 'CPUQuota=100%' "$tmp/systemd"
grep -q -- 'MemoryMax=1G' "$tmp/systemd"
grep -q -- 'IOWeight=50' "$tmp/systemd"
grep -q -- "$tmp/record payload" "$tmp/systemd"

if BACKUP_PI_RESOURCE_MODE=systemd PATH="/usr/bin:/bin" bash "$runner" true 2>"$tmp/strict.err"; then
  echo 'strict mode must fail when systemd-run is unavailable' >&2
  exit 1
fi
grep -q 'systemd-run is required' "$tmp/strict.err"

echo 'Pi resource cap tests passed'
