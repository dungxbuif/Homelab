#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat >&2 <<'EOF'
Usage: post-check-report.sh --kind KIND --run-dir DIR --summary TEXT [options]

Options:
  --details TEXT       Optional verification details
  --run-id ID          Backup run identifier
  --snapshot-id ID     Remote snapshot identifier
  --dry-run            Validate and print the Mezon payload without sending it
EOF
  exit 2
}

kind=''
run_dir=''
summary=''
details=''
run_id=''
snapshot_id=''
dry_run='false'
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)

while (($#)); do
  case "$1" in
    --kind) (($# >= 2)) || usage; kind=$2; shift 2 ;;
    --run-dir) (($# >= 2)) || usage; run_dir=$2; shift 2 ;;
    --summary) (($# >= 2)) || usage; summary=$2; shift 2 ;;
    --details) (($# >= 2)) || usage; details=$2; shift 2 ;;
    --run-id) (($# >= 2)) || usage; run_id=$2; shift 2 ;;
    --snapshot-id) (($# >= 2)) || usage; snapshot_id=$2; shift 2 ;;
    --dry-run) dry_run='true'; shift ;;
    *) usage ;;
  esac
done

[[ -n "$kind" && -n "$run_dir" && -n "$summary" ]] || usage
[[ -d "$run_dir" ]] || { echo 'backup run directory does not exist' >&2; exit 1; }

failure_reason=''
if [[ ! -f "$run_dir/manifest.json" ]]; then
  failure_reason='manifest.json is missing'
elif [[ ! -f "$run_dir/COMPLETE" ]]; then
  failure_reason='COMPLETE marker is missing'
elif [[ -f "$run_dir/checksums.sha256" ]]; then
  if ! (cd "$run_dir" && sha256sum --quiet -c checksums.sha256); then
    failure_reason='checksum verification failed'
  fi
fi

if [[ -z "$failure_reason" ]]; then
  if ! python3 - "$run_dir/manifest.json" "$kind" "$snapshot_id" <<'PY'
import json
import sys

path, expected_kind, cli_snapshot = sys.argv[1:]
with open(path, encoding='utf-8') as handle:
    manifest = json.load(handle)

if manifest.get('status') != 'complete':
    raise SystemExit('manifest status is not complete')
if manifest.get('kind') != expected_kind:
    raise SystemExit('manifest kind does not match requested kind')
snapshot = cli_snapshot or manifest.get('remote_snapshot_id')
if not snapshot:
    raise SystemExit('remote snapshot id is missing')
coverage = manifest.get('coverage')
if not isinstance(coverage, list) or not coverage:
    raise SystemExit('manifest coverage is empty')
PY
  then
    failure_reason='manifest verification failed'
  fi
fi

if [[ -n "$failure_reason" ]]; then
  args=(
    --kind "$kind"
    --status failure
    --summary 'post-check failed'
    --details "$failure_reason${details:+; $details}"
    --run-id "$run_id"
    --snapshot-id "$snapshot_id"
  )
  [[ "$dry_run" == 'true' ]] && args+=(--dry-run)
  "$script_dir/notify-mezon.sh" "${args[@]}"
  exit 1
fi

args=(
  --kind "$kind"
  --status success
  --summary "$summary"
  --details "$details"
  --run-id "$run_id"
  --snapshot-id "$snapshot_id"
)
[[ "$dry_run" == 'true' ]] && args+=(--dry-run)
"$script_dir/notify-mezon.sh" "${args[@]}"
