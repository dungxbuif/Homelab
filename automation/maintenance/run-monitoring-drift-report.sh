#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
app_root=${HOMELAB_APP_ROOT:-$(cd -- "$script_dir/../.." && pwd)}
audit="$app_root/automation/maintenance/audit-monitoring-targets.py"
notify="$app_root/backup/scripts/notify-mezon.sh"
tmp=$(mktemp)
trap 'rm -f -- "$tmp"' EXIT

set +e
python3 "$audit" >"$tmp" 2>&1
audit_rc=$?
set -e

details=$(cat "$tmp")
if ((audit_rc == 0)); then
  status=success
  summary='active monitoring targets match the retired-target policy'
else
  status=failure
  summary='active monitoring target audit failed'
fi

bash "$notify" \
  --kind monitoring-drift \
  --status "$status" \
  --summary "$summary" \
  --details "$details"
exit "$audit_rc"
