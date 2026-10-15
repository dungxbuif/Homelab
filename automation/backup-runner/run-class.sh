#!/usr/bin/env bash
set -euo pipefail

class=${1:?usage: run-class.sh databases|database-instances|rustfs|gitlab RUN_ID [GITLAB_RUN_DIR]}
run_id=${2:-$(date -u +backup-%Y%m%d-%H%M%S)}
gitlab_run_dir=${3:-}
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
app_root=${BACKUP_APP_ROOT:-$(cd -- "$script_dir/../.." && pwd)}
backup_scripts=${BACKUP_SCRIPTS_DIR:-$app_root/backup/scripts}
rustfs_scripts=${RUSTFS_SCRIPTS_DIR:-$app_root/automation/rustfs-backup}
gitlab_scripts=${GITLAB_SCRIPTS_DIR:-$app_root/automation/gitlab-backup}
inventory=${BACKUP_INVENTORY:-$app_root/backup/inventory.yaml}
staging_root=${BACKUP_STAGING_ROOT:-/ssd-data/infra/backups/homelab}
status_root=${BACKUP_STATUS_ROOT:-$staging_root/.state}
lock_file=${BACKUP_LOCK_FILE:-/run/lock/homelab-backup.lock}

case "$class" in
  databases|database-instances|rustfs|gitlab) ;;
  *) echo "unsupported backup class: $class" >&2; exit 2 ;;
esac

backup_succeeded=false
stage='startup'
on_exit() {
  local exit_code=$?
  trap - EXIT
  if ((exit_code != 0)) && [[ "$backup_succeeded" != true ]] && [[ -n "${MEZON_WEBHOOK_URL_FILE:-}" ]]; then
    bash "$backup_scripts/notify-mezon.sh" \
      --kind "$class" \
      --status failure \
      --summary 'backup runner failed before remote post-check' \
      --details "stage=${stage}; runner exit code=${exit_code}; inspect the class journal and run directory" \
      --run-id "$run_id" \
      || true
  fi
  exit "$exit_code"
}
trap on_exit EXIT

mkdir -p "$(dirname -- "$lock_file")"
exec 9>"$lock_file"
if ! flock -n 9; then
  echo 'another homelab backup job holds the global lock' >&2
  exit 75
fi

mkdir -p "$status_root"
# A failed or interrupted run must invalidate the previous success gate so
# retention cannot prune based on stale evidence.
rm -f "$status_root/$class.success"

: "${RESTIC_PASSWORD_FILE:?RESTIC_PASSWORD_FILE is required}"
: "${RCLONE_CONFIG_FILE:?RCLONE_CONFIG_FILE is required}"
: "${BACKUP_LOCAL_RCLONE_BIN:?BACKUP_LOCAL_RCLONE_BIN is required}"
: "${RCLONE_REMOTE:?RCLONE_REMOTE is required}"
: "${DRIVE_ROOT:?DRIVE_ROOT is required}"
: "${MEZON_WEBHOOK_URL_FILE:?MEZON_WEBHOOK_URL_FILE is required}"

case "$class" in
  databases)
    stage='database export'
    run_dir=$(python3 "$backup_scripts/run-database-backup.py" \
      --inventory "$inventory" \
      --staging-root "$staging_root" \
      --run-id "$run_id")
    summary='PostgreSQL and CouchDB backup verified'
    ;;
  database-instances)
    stage='PostgreSQL instance export'
    run_dir=$(python3 "$backup_scripts/run-instance-backup.py" \
      --inventory "$inventory" \
      --staging-root "$staging_root" \
      --run-id "$run_id" \
      --host "${BACKUP_INSTANCE_HOST:-vm100}")
    summary='Additional PostgreSQL instance backup verified'
    ;;
  rustfs)
    stage='RustFS export'
    run_dir=$(bash "$rustfs_scripts/run-rustfs-backup.sh" \
      "$staging_root" \
      "$run_id" \
      "$inventory" \
      "${RUSTFS_CREDENTIALS_FILE:?RUSTFS_CREDENTIALS_FILE is required}")
    summary='RustFS object backup verified'
    ;;
  gitlab)
    stage='GitLab run validation'
    [[ -n "$gitlab_run_dir" ]] || {
      echo 'GitLab class requires a completed run directory from the VM100 native job' >&2
      exit 2
    }
    run_dir=$(cd -- "$gitlab_run_dir" && pwd)
    [[ -f "$run_dir/COMPLETE" && -f "$run_dir/manifest.json" ]] || {
      echo 'GitLab run directory is incomplete' >&2
      exit 1
    }
    summary='GitLab native backup verified'
    ;;
esac

stage='Restic upload and remote check'
snapshot_id=$(bash "$backup_scripts/upload-restic.sh" "$class" "$run_dir" "$run_id")
stage='Mezon post-check'
post_check_args=(
  --kind "$class"
  --run-dir "$run_dir"
  --summary "$summary"
  --run-id "$run_id"
  --snapshot-id "$snapshot_id"
)
if [[ "${BACKUP_DRY_RUN:-false}" == 'true' ]]; then
  post_check_args+=(--dry-run)
fi
bash "$backup_scripts/post-check-report.sh" "${post_check_args[@]}"
stage='success marker'
status_tmp=$(mktemp "$status_root/.${class}.success.XXXXXX")
{
  printf 'status=success\n'
  printf 'completed_at=%s\n' "$(date -u +%s)"
  printf 'run_id=%s\n' "$run_id"
  printf 'snapshot_id=%s\n' "$snapshot_id"
} > "$status_tmp"
mv -f "$status_tmp" "$status_root/$class.success"
backup_succeeded=true
printf '%s\n' "$snapshot_id"
