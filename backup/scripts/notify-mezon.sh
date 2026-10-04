#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat >&2 <<'EOF'
Usage: notify-mezon.sh --kind KIND --status STATUS --summary TEXT [options]

Options:
  --details TEXT       Optional verification details
  --run-id ID          Backup run identifier
  --snapshot-id ID     Remote snapshot identifier
  --dry-run            Print the sanitized payload without sending it
EOF
  exit 2
}

kind=''
status=''
summary=''
details=''
run_id=''
snapshot_id=''
dry_run='false'

while (($#)); do
  case "$1" in
    --kind) (($# >= 2)) || usage; kind=$2; shift 2 ;;
    --status) (($# >= 2)) || usage; status=$2; shift 2 ;;
    --summary) (($# >= 2)) || usage; summary=$2; shift 2 ;;
    --details) (($# >= 2)) || usage; details=$2; shift 2 ;;
    --run-id) (($# >= 2)) || usage; run_id=$2; shift 2 ;;
    --snapshot-id) (($# >= 2)) || usage; snapshot_id=$2; shift 2 ;;
    --dry-run) dry_run='true'; shift ;;
    *) usage ;;
  esac
done

[[ -n "$kind" && -n "$status" && -n "$summary" ]] || usage
case "$status" in
  success) icon='OK' ;;
  failure) icon='FAIL' ;;
  warning) icon='WARN' ;;
  *) echo 'status must be success, failure, or warning' >&2; exit 2 ;;
esac

if [[ -n "${MEZON_WEBHOOK_URL_FILE:-}" ]]; then
  [[ -r "$MEZON_WEBHOOK_URL_FILE" ]] || { echo 'Mezon webhook secret file is not readable' >&2; exit 1; }
  export MEZON_WEBHOOK_URL
  MEZON_WEBHOOK_URL=$(<"$MEZON_WEBHOOK_URL_FILE")
fi

if [[ "$dry_run" != 'true' ]]; then
  [[ -n "${MEZON_WEBHOOK_URL:-}" ]] || {
    echo 'Set MEZON_WEBHOOK_URL_FILE or MEZON_WEBHOOK_URL' >&2
    exit 1
  }
fi

export MEZON_BACKUP_KIND="$kind"
export MEZON_BACKUP_STATUS="$status"
export MEZON_BACKUP_ICON="$icon"
export MEZON_BACKUP_SUMMARY="$summary"
export MEZON_BACKUP_DETAILS="$details"
export MEZON_BACKUP_RUN_ID="$run_id"
export MEZON_BACKUP_SNAPSHOT_ID="$snapshot_id"
export MEZON_BACKUP_DRY_RUN="$dry_run"

python3 <<'PY'
import json
import os
import sys
import urllib.error
import urllib.request

kind = os.environ['MEZON_BACKUP_KIND']
status = os.environ['MEZON_BACKUP_STATUS']
icon = os.environ['MEZON_BACKUP_ICON']
summary = os.environ['MEZON_BACKUP_SUMMARY'].strip()
details = os.environ['MEZON_BACKUP_DETAILS'].strip()
run_id = os.environ['MEZON_BACKUP_RUN_ID'].strip()
snapshot_id = os.environ['MEZON_BACKUP_SNAPSHOT_ID'].strip()

lines = [f'[HOMELAB BACKUP] [{icon}] {kind}: {summary}']
if run_id:
    lines.append(f'Run: {run_id}')
if snapshot_id:
    lines.append(f'Snapshot: {snapshot_id}')
if details:
    lines.extend(['', details[:2400]])
text = '\n'.join(lines)
payload = {
    'type': 'hook',
    'message': {
        't': text,
        'mk': [{'type': 'pre', 's': 0, 'e': len(text)}],
        'mentions': [],
        'images': [],
        'hg': [],
    },
}

if os.environ['MEZON_BACKUP_DRY_RUN'] == 'true':
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    sys.exit(0)

url = os.environ['MEZON_WEBHOOK_URL'].strip()
request = urllib.request.Request(
    url,
    data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
    headers={'Content-Type': 'application/json'},
    method='POST',
)
try:
    with urllib.request.urlopen(request, timeout=15) as response:
        if not 200 <= response.status < 300:
            raise RuntimeError(f'Mezon returned HTTP {response.status}')
except (urllib.error.URLError, TimeoutError, RuntimeError) as exc:
    # Never include the webhook URL or response body in operator output.
    print(f'Mezon notification failed: {exc.__class__.__name__}', file=sys.stderr)
    sys.exit(1)
PY
