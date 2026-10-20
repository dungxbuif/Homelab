#!/usr/bin/env bash
set -euo pipefail

class=${1:?usage: run-vm100-scheduled.sh databases|database-instances|gitlab|rustfs|configs|retention|weekly-integrity|health}
case "$class" in
  databases|database-instances|gitlab|rustfs|configs|retention|weekly-integrity|health) ;;
  *) echo "unsupported backup class: $class" >&2; exit 2 ;;
esac

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
app_root=${BACKUP_APP_ROOT:-$(cd -- "$script_dir/../.." && pwd)}
backup_scripts=${BACKUP_SCRIPTS_DIR:-$app_root/backup/scripts}
staging_root=${BACKUP_STAGING_ROOT:-/opt/apps/homelab-backup/runs}
status_root=${BACKUP_STATUS_ROOT:-$staging_root/.state}
pi_target=${PI_BACKUP_SSH_TARGET:-dungxbuif@10.10.0.5}
pi_key=${PI_BACKUP_SSH_KEY:-/home/ubuntu/.ssh/homelab-backup-pi}
pi_executor=${PI_BACKUP_EXECUTOR:-/home/dungxbuif/.local/sbin/homelab-backup-executor}
ssh_options=(
  -i "$pi_key"
  -o IdentitiesOnly=yes
  -o BatchMode=yes
  -o StrictHostKeyChecking=yes
  -o ConnectTimeout=10
  -o ServerAliveInterval=30
  -o ServerAliveCountMax=10
)
pi_command_timeout=${PI_BACKUP_COMMAND_TIMEOUT_SECONDS:-14400}
[[ "$pi_command_timeout" =~ ^[1-9][0-9]*$ ]] || {
  echo 'PI_BACKUP_COMMAND_TIMEOUT_SECONDS must be a positive integer' >&2
  exit 2
}

[[ "$class" == health ]] || mkdir -p "$staging_root" "$status_root"
export BACKUP_LOCK_WAIT_SECONDS="${BACKUP_SCHEDULE_LOCK_WAIT_SECONDS:-3600}"

run_pi() {
  # The remote forced-command guard matches this exact client-built command.
  # shellcheck disable=SC2029
  timeout --signal=TERM --kill-after=60s "${pi_command_timeout}s" \
    ssh "${ssh_options[@]}" "$pi_target" "$pi_executor $1"
}

sync_pi_markers() {
  local bundle marker_tmp class
  bundle=$(mktemp "$status_root/.pi-markers.XXXXXX")
  trap 'rm -f -- "$bundle"' RETURN
  run_pi markers > "$bundle"
  for class in databases rustfs; do
    marker_tmp="$status_root/.${class}.success.pi-$$.tmp"
    rm -f -- "$status_root/$class.success" "$marker_tmp"
    awk -v begin="MARKER $class" '
      $0 == begin { inside=1; next }
      $0 == "ENDMARKER" { if (inside) exit }
      inside { print }
    ' "$bundle" > "$marker_tmp"
    [[ -s "$marker_tmp" ]] || {
      rm -f -- "$marker_tmp"
      echo "Pi5 success marker is missing: $class" >&2
      return 1
    }
    grep -Eq '^completed_at=[0-9]+$' "$marker_tmp" || {
      rm -f -- "$marker_tmp"
      echo "Pi5 success marker is invalid: $class" >&2
      return 1
    }
    chmod 600 "$marker_tmp"
    mv -f -- "$marker_tmp" "$status_root/$class.success"
  done
}

case "$class" in
  health)
    run_pi health
    ;;
  databases|rustfs)
    run_pi "$class"
    ;;
  configs)
    run_id="configs-$(date -u +%Y%m%d-%H%M%S)"
    umask 077
    pi_archive=$(mktemp "$staging_root/.${run_id}.pi-configs.tar.XXXXXX")
    trap 'rm -f -- "$pi_archive"' EXIT
    run_pi configs > "$pi_archive"
    BACKUP_APP_ROOT="$app_root" \
      BACKUP_STAGING_ROOT="$staging_root" \
      BACKUP_STATUS_ROOT="$status_root" \
      BACKUP_CONFIGS_PI_ARCHIVE="$pi_archive" \
      bash "$app_root/automation/backup-runner/run-class.sh" configs "$run_id"
    ;;
  database-instances)
    rm -f "$status_root/database-instances.success"
    run_id="database-instances-$(date -u +%Y%m%d-%H%M%S)"
    BACKUP_APP_ROOT="$app_root" \
      BACKUP_STAGING_ROOT="$staging_root" \
      BACKUP_STATUS_ROOT="$status_root" \
      BACKUP_INSTANCE_HOST=vm100 \
      bash "$app_root/automation/backup-runner/run-class.sh" database-instances "$run_id"
    ;;
  gitlab)
    rm -f "$status_root/gitlab.success"
    run_id="gitlab-$(date -u +%Y%m%d-%H%M%S)"
    run_root="$staging_root/$run_id"
    native_script=${GITLAB_BACKUP_SCRIPT:-$app_root/automation/gitlab-backup/run-gitlab-backup.sh}
    output=$(bash "$native_script" "$run_root")
    complete_dir=$(printf '%s\n' "$output" | tail -n 1)
    [[ -f "$complete_dir/COMPLETE" ]] || {
      echo 'GitLab native wrapper did not return a complete run' >&2
      exit 1
    }
    BACKUP_APP_ROOT="$app_root" \
      BACKUP_STAGING_ROOT="$staging_root" \
      BACKUP_STATUS_ROOT="$status_root" \
      bash "$app_root/automation/backup-runner/run-class.sh" gitlab "$run_id" "$complete_dir"
    ;;
  retention)
    python3 "$script_dir/wait-retention-prerequisites.py"
    sync_pi_markers
    BACKUP_APP_ROOT="$app_root" \
      BACKUP_STAGING_ROOT="$staging_root" \
      BACKUP_STATUS_ROOT="$status_root" \
      bash "$script_dir/run-retention.sh"
    BACKUP_APP_ROOT="$app_root" \
      BACKUP_STAGING_ROOT="$staging_root" \
      BACKUP_STATUS_ROOT="$status_root" \
      bash "$script_dir/run-instance-retention.sh"
    BACKUP_STAGING_ROOT="$staging_root" \
      bash "$backup_scripts/cleanup-local-runs.sh" gitlab
    if [[ -f "$status_root/configs.success" ]]; then
      BACKUP_APP_ROOT="$app_root" \
        BACKUP_STAGING_ROOT="$staging_root" \
        BACKUP_STATUS_ROOT="$status_root" \
        bash "$script_dir/run-config-retention.sh"
    else
      echo 'configs retention skipped: no successful configs run yet'
    fi
    ;;
  weekly-integrity)
    exec 9>"${BACKUP_LOCK_FILE:-/run/lock/homelab-backup.lock}"
    flock -n 9 || { echo 'another homelab backup job holds the global lock' >&2; exit 75; }
    for deep_class in databases rustfs database-instances gitlab; do
      RESTIC_READ_DATA_SUBSET=1/10 \
        BACKUP_APP_ROOT="$app_root" \
        BACKUP_STAGING_ROOT="$staging_root" \
        bash "$app_root/backup/scripts/run-integrity-check.sh" "$deep_class"
    done
    ;;
esac
