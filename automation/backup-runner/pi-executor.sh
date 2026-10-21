#!/usr/bin/env bash
set -euo pipefail

class=${1:?usage: pi-executor.sh databases|rustfs|configs|markers|retention|deep-verify|health}
case "$class" in
  databases|rustfs|configs|markers|retention|deep-verify|health) ;;
  *) echo "unsupported backup class: $class" >&2; exit 2 ;;
esac

env_file=${BACKUP_ENV_FILE:-/ssd-data/infra/backup/runner.env}
[[ -r "$env_file" ]] || { echo "backup environment is missing: $env_file" >&2; exit 1; }
# The SSH caller supplies only the allow-listed class; all secret paths remain
# local to Pi5 and are loaded from its root-owned environment file.
# Export the sourced runtime settings to the backup scripts that execute below.
# Without this, the child process would lose secret paths and remote settings.
set -a
# shellcheck disable=SC1090
source "$env_file"
set +a
app_root=${BACKUP_APP_ROOT:-/ssd-data/infra/backup-runner/app}
status_root=${BACKUP_STATUS_ROOT:-/ssd-data/infra/backups/homelab/.state}
if [[ "$class" == markers ]]; then
  for marker_class in databases rustfs; do
    marker="$status_root/$marker_class.success"
    [[ -f "$marker" ]] || continue
    printf 'MARKER %s\n' "$marker_class"
    cat -- "$marker"
    printf 'ENDMARKER\n'
  done
  exit 0
fi
case "$class" in
  health)
    export BACKUP_HEALTH_EXPECTED_CLASSES='databases rustfs'
    export BACKUP_HEALTH_CHECK_UNITS=false BACKUP_HEALTH_REMOTE_PI=false
    export BACKUP_HEALTH_ACTIVE_PROCESS_PATTERN="${BACKUP_HEALTH_ACTIVE_PROCESS_PATTERN:-$app_root/automation/backup-runner/run-(retention|class|restic_container)(\.sh)?}"
    exec bash "$app_root/backup/scripts/check-backup-health.sh"
    ;;
  databases|rustfs)
    resource_runner="$app_root/automation/backup-runner/run-pi-capped.sh"
    [[ -x "$resource_runner" ]] || { echo "bounded Pi runner is missing: $resource_runner" >&2; exit 1; }
    resource_mode=${BACKUP_PI_RESOURCE_MODE:-systemd}
    run_id="${class}-$(date -u +%Y%m%d-%H%M%S)"
    if [[ "$resource_mode" == systemd ]]; then
      exec sudo -n /usr/local/sbin/homelab-backup-systemd-class "$class"
    fi
    exec "$resource_runner" bash "$app_root/automation/backup-runner/run-class.sh" "$class" "$run_id"
    ;;
  configs)
    resource_runner="$app_root/automation/backup-runner/run-pi-capped.sh"
    [[ -x "$resource_runner" ]] || { echo "bounded Pi runner is missing: $resource_runner" >&2; exit 1; }
    resource_mode=${BACKUP_PI_RESOURCE_MODE:-systemd}
    if [[ "$resource_mode" == systemd ]]; then
      exec sudo -n /usr/local/sbin/homelab-backup-systemd-class "$class"
    fi
    exec "$resource_runner" bash "$app_root/automation/backup-runner/export-configs-pi.sh"
    ;;
  retention)
    resource_runner="$app_root/automation/backup-runner/run-pi-capped.sh"
    [[ -x "$resource_runner" ]] || { echo "bounded Pi runner is missing: $resource_runner" >&2; exit 1; }
    resource_mode=${BACKUP_PI_RESOURCE_MODE:-systemd}
    if [[ "$resource_mode" == systemd ]]; then
      exec sudo -n /usr/local/sbin/homelab-backup-systemd-class "$class"
    fi
    exec "$resource_runner" bash "$app_root/automation/backup-runner/run-retention.sh"
    ;;
  deep-verify)
    resource_runner="$app_root/automation/backup-runner/run-pi-capped.sh"
    [[ -x "$resource_runner" ]] || { echo "bounded Pi runner is missing: $resource_runner" >&2; exit 1; }
    resource_mode=${BACKUP_PI_RESOURCE_MODE:-systemd}
    exec 9>"${BACKUP_LOCK_FILE:-/ssd-data/infra/backups/homelab/.homelab-backup.lock}"
    flock -n 9 || { echo 'another homelab backup job holds the global lock' >&2; exit 75; }
    if [[ "$resource_mode" == systemd ]]; then
      exec sudo -n /usr/local/sbin/homelab-backup-systemd-class "$class"
    fi
    exec "$resource_runner" bash -c '
      for deep_class in databases rustfs; do
        bash "$1/backup/scripts/run-integrity-check.sh" "$deep_class"
      done
    ' -- "$app_root"
    ;;
esac
