#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
app_root=${BACKUP_APP_ROOT:-$(cd -- "$script_dir/../.." && pwd)}
backup_scripts=${BACKUP_SCRIPTS_DIR:-$app_root/backup/scripts}
staging_root=${BACKUP_STAGING_ROOT:-/opt/apps/homelab-backup/runs}
drill_root=${RESTORE_DRILL_ROOT:-/opt/apps/homelab-backup/restore-drills}
status_root=${BACKUP_STATUS_ROOT:-$staging_root/.state}
lock_file=${BACKUP_LOCK_FILE:-/run/lock/homelab-backup.lock}
min_free_bytes=${RESTORE_DRILL_MIN_FREE_BYTES:-16106127360}
classes=${RESTORE_DRILL_CLASSES:-"databases database-instances gitlab rustfs"}
run_id=${RESTORE_DRILL_RUN_ID:-restore-drill-$(date -u +%Y%m%d-%H%M%S)}
run_dir="$drill_root/$run_id"

die() { echo "restore drill: $*" >&2; exit 1; }

mkdir -p "$drill_root" "$status_root" "$(dirname -- "$lock_file")"
exec 9>"$lock_file"
flock -n 9 || die 'another backup operation is active'

read -r _ _ available_kb _ < <(df -Pk "$drill_root" | awk 'NR > 1 {print $2, $3, $4; exit}')
[[ "$available_kb" =~ ^[0-9]+$ ]] || die 'could not read free space'
available_bytes=$((available_kb * 1024))
((available_bytes >= min_free_bytes)) || die "free space ${available_bytes} is below ${min_free_bytes}"

cleanup() {
  local exit_code=$?
  trap - EXIT
  [[ -d "$run_dir" ]] && rm -rf -- "$run_dir"
  if [[ "${RCLONE_CONFIG_WORKDIR_CREATED:-0}" == 1 && -n "${RCLONE_CONFIG_WORKDIR:-}" ]]; then
    rm -rf -- "$RCLONE_CONFIG_WORKDIR"
  fi
  if ((exit_code != 0)); then
    rm -f -- "$status_root/restore-drill.success"
    if [[ -x "$backup_scripts/notify-mezon.sh" && -n "${MEZON_WEBHOOK_URL_FILE:-}" ]]; then
      "$backup_scripts/notify-mezon.sh" --kind restore-drill --status failure \
        --summary 'restore drill failed' \
        --details "run=${run_id}; free_bytes=${available_bytes}; inspect journal" \
        --run-id "$run_id" || true
    fi
  fi
  exit "$exit_code"
}
mkdir -- "$run_dir"
chmod 0700 "$run_dir"

# shellcheck source=restic-lib.sh
source "$backup_scripts/restic-lib.sh"
export RESTIC_CONTAINER_USER="$(id -u):$(id -g)"
trap cleanup EXIT

latest_snapshot() {
  local class=$1 json_file snapshot
  json_file=$(mktemp "$run_dir/.snapshots-${class}.XXXXXX")
  export RESTIC_REPOSITORY
  RESTIC_REPOSITORY=$(restic_repo_for "$class")
  restic_run snapshots --no-lock --json --tag "class=$class" >"$json_file"
  snapshot=$(python3 - "$json_file" <<'PY'
import json
import re
import sys

rows = json.load(open(sys.argv[1], encoding="utf-8"))
if not rows:
    raise SystemExit("no matching snapshots")
value = max(rows, key=lambda item: item.get("time", "")).get("id", "")
if not re.fullmatch(r"[0-9a-f]{64}", value):
    raise SystemExit("invalid snapshot id")
print(value)
PY
)
  printf '%s\n' "$snapshot"
}

verify_payload() {
  local class=$1 target=$2 manifest
  manifest=$(find "$target" -maxdepth 3 -type f -name manifest.json -print -quit)
  [[ -n "$manifest" ]] || die "$class: manifest.json missing"
  python3 - "$manifest" "$class" <<'PY'
import json
import sys

data = json.load(open(sys.argv[1], encoding="utf-8"))
if data.get("status") != "complete":
    raise SystemExit("manifest status is not complete")
if data.get("kind") != sys.argv[2]:
    raise SystemExit("manifest kind mismatch")
PY
  [[ -f "$(dirname -- "$manifest")/COMPLETE" || -f "$target/COMPLETE" ]] || die "$class: COMPLETE marker missing"
  while IFS= read -r checksum_file; do
    (cd -- "$(dirname -- "$checksum_file")" && sha256sum --quiet -c "$(basename -- "$checksum_file")") || die "$class: checksum verification failed"
  done < <(find "$target" -maxdepth 4 -type f -name checksums.sha256 -print)
}

declare -a report=()
for class in $classes; do
  snapshot=$(latest_snapshot "$class")
  target="$run_dir/$class"
  bash "$backup_scripts/restore-staging.sh" "$class" "$snapshot" "$target" >/dev/null
  verify_payload "$class" "$target"
  report+=("$class=$snapshot")
done

status_tmp=$(mktemp "$status_root/.restore-drill.success.XXXXXX")
{
  printf 'status=success\n'
  printf 'completed_at=%s\n' "$(date -u +%s)"
  printf 'run_id=%s\n' "$run_id"
  printf 'classes=%s\n' "$classes"
  printf 'snapshots=%s\n' "$(IFS=,; echo "${report[*]}")"
} >"$status_tmp"
mv -f "$status_tmp" "$status_root/restore-drill.success"

if [[ -x "$backup_scripts/notify-mezon.sh" && -n "${MEZON_WEBHOOK_URL_FILE:-}" ]]; then
  "$backup_scripts/notify-mezon.sh" --kind restore-drill --status success \
    --summary 'latest backup payloads restored and verified' \
    --details "free_bytes=${available_bytes}; ${report[*]}" \
    --run-id "$run_id"
fi

echo "restore drill passed: run=$run_id classes=$classes"
