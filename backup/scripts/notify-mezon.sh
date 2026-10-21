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
import re
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

labels = {
    'databases': 'PostgreSQL + CouchDB',
    'database-instances': 'PostgreSQL instance trên VM100',
    'rustfs': 'RustFS object storage',
    'gitlab': 'GitLab',
    'configs': 'Cấu hình Pi5 + VM100',
    'retention': 'Dọn bản backup cũ',
    'restore-drill': 'Kiểm tra khôi phục backup',
    'health': 'Tình trạng hệ thống backup',
}
label = labels.get(kind, kind)
status_words = {
    'success': 'Backup thành công',
    'failure': 'Backup gặp lỗi',
    'warning': 'Backup cần chú ý',
}
display_icons = {'OK': '✅', 'WARN': '⚠️', 'FAIL': '❌'}

def human_bytes(value):
    try:
        number = float(value)
    except ValueError:
        return value
    units = ('B', 'KB', 'MB', 'GB', 'TB')
    index = 0
    while abs(number) >= 1024 and index < len(units) - 1:
        number /= 1024
        index += 1
    return f'{number:.1f} {units[index]}'

def friendly_details(value):
    output = []
    for raw in value.splitlines():
        line = raw.strip()
        if not line or line.startswith('[backup-health]'):
            continue
        match = re.search(r'free_bytes=(\d+)', line)
        if match:
            output.append(f"Dung lượng còn trống: {human_bytes(match.group(1))}")
            continue
        match = re.search(r'disk_used_percent=(\d+)', line)
        if match:
            output.append(f"Đã sử dụng: {match.group(1)}% dung lượng đĩa")
            continue
        if line.startswith('low free space:'):
            output.append('Dung lượng đĩa sắp đầy')
        elif line.startswith('disk usage is '):
            output.append(line.replace('disk usage is ', 'Dung lượng đĩa đang ở mức ')
                          .replace('% (warning threshold 85%)', '%'))
        elif line.startswith('missing success marker:'):
            output.append('Chưa thấy dấu hiệu hoàn tất của một lượt backup')
        elif line.startswith('stale success marker:'):
            output.append('Dấu hiệu backup đã cũ, cần kiểm tra lịch chạy')
        elif line.startswith('failed unit:'):
            output.append('Một tác vụ backup bị lỗi')
        elif line.startswith('stage=') or line.startswith('runner exit code='):
            continue
        elif line.startswith('Pi backup health'):
            continue
        else:
            output.append(line)
    return output[:5]

lines = [f'{display_icons.get(icon, icon)} {status_words[status]}: {label}']
if status == 'success':
    lines.append('Đã lưu và kiểm tra bản backup thành công.')
else:
    friendly = friendly_details(details)
    if friendly:
        lines.extend(f'• {item}' for item in friendly)
    if run_id:
        lines.append(f'Mã kiểm tra: {run_id}')
    if snapshot_id and status == 'failure':
        lines.append(f'Mã bản lưu: {snapshot_id}')
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
