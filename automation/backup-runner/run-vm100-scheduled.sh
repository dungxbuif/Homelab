#!/usr/bin/env bash
set -euo pipefail

class=${1:?usage: run-vm100-scheduled.sh databases|database-instances|gitlab|rustfs|retention|health}
case "$class" in
  databases|database-instances|gitlab|rustfs|retention|health) ;;
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

[[ "$class" == health ]] || mkdir -p "$staging_root" "$status_root"

run_pi() {
  # The remote forced-command guard matches this exact client-built command.
  # shellcheck disable=SC2029
  ssh "${ssh_options[@]}" "$pi_target" "$pi_executor $1"
}

case "$class" in
  health)
    run_pi health
    ;;
  databases|rustfs)
    run_pi "$class"
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
    marker="$status_root/gitlab.success"
    [[ -f "$marker" ]] || {
      echo 'GitLab success marker is missing before retention' >&2
      exit 1
    }
    run_pi retention < "$marker"
    BACKUP_APP_ROOT="$app_root" \
      BACKUP_STAGING_ROOT="$staging_root" \
      BACKUP_STATUS_ROOT="$status_root" \
      bash "$script_dir/run-instance-retention.sh"
    BACKUP_STAGING_ROOT="$staging_root" \
      bash "$backup_scripts/cleanup-local-runs.sh" gitlab
    ;;
esac
