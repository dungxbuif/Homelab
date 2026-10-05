#!/usr/bin/env bash
set -euo pipefail

class=${1:?usage: run-class.sh databases|rustfs|gitlab RUN_ID [GITLAB_RUN_DIR]}
run_id=${2:-$(date -u +backup-%Y%m%d-%H%M%S)}
gitlab_run_dir=${3:-}
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
app_root=${BACKUP_APP_ROOT:-$(cd -- "$script_dir/../.." && pwd)}
backup_scripts=${BACKUP_SCRIPTS_DIR:-$app_root/backup/scripts}
rustfs_scripts=${RUSTFS_SCRIPTS_DIR:-$app_root/automation/rustfs-backup}
gitlab_scripts=${GITLAB_SCRIPTS_DIR:-$app_root/automation/gitlab-backup}
inventory=${BACKUP_INVENTORY:-$app_root/backup/inventory.yaml}
staging_root=${BACKUP_STAGING_ROOT:-/ssd-data/infra/backups/homelab}
lock_file=${BACKUP_LOCK_FILE:-/run/lock/homelab-backup.lock}

case "$class" in
  databases|rustfs|gitlab) ;;
  *) echo "unsupported backup class: $class" >&2; exit 2 ;;
esac

mkdir -p "$(dirname -- "$lock_file")"
exec 9>"$lock_file"
if ! flock -n 9; then
  echo 'another homelab backup job holds the global lock' >&2
  exit 75
fi

: "${RESTIC_PASSWORD_FILE:?RESTIC_PASSWORD_FILE is required}"
: "${RCLONE_CONFIG_FILE:?RCLONE_CONFIG_FILE is required}"
: "${BACKUP_LOCAL_RCLONE_BIN:?BACKUP_LOCAL_RCLONE_BIN is required}"
: "${RCLONE_REMOTE:?RCLONE_REMOTE is required}"
: "${DRIVE_ROOT:?DRIVE_ROOT is required}"
: "${MEZON_WEBHOOK_URL_FILE:?MEZON_WEBHOOK_URL_FILE is required}"

case "$class" in
  databases)
    run_dir=$(python3 "$backup_scripts/run-database-backup.py" \
      --inventory "$inventory" \
      --staging-root "$staging_root" \
      --run-id "$run_id")
    summary='PostgreSQL and CouchDB backup verified'
    ;;
  rustfs)
    run_dir=$(bash "$rustfs_scripts/run-rustfs-backup.sh" \
      "$staging_root" \
      "$run_id" \
      "$inventory" \
      "${RUSTFS_CREDENTIALS_FILE:?RUSTFS_CREDENTIALS_FILE is required}")
    summary='RustFS object backup verified'
    ;;
  gitlab)
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

snapshot_id=$(bash "$backup_scripts/upload-restic.sh" "$class" "$run_dir" "$run_id")
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
printf '%s\n' "$snapshot_id"
