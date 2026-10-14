#!/usr/bin/env bash
set -euo pipefail

class=${1:?usage: pi-executor.sh databases|rustfs|retention|health}
case "$class" in
  databases|rustfs|retention|health) ;;
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
case "$class" in
  health)
    export BACKUP_HEALTH_EXPECTED_CLASSES='databases rustfs'
    export BACKUP_HEALTH_CHECK_UNITS=false BACKUP_HEALTH_REMOTE_PI=false
    exec bash "$app_root/backup/scripts/check-backup-health.sh"
    ;;
  databases|rustfs)
    run_id="${class}-$(date -u +%Y%m%d-%H%M%S)"
    exec bash "$app_root/automation/backup-runner/run-class.sh" "$class" "$run_id"
    ;;
  retention)
    exec bash "$app_root/automation/backup-runner/run-retention.sh"
    ;;
esac
