#!/usr/bin/env bash
set -euo pipefail

((EUID == 0)) || { echo 'root-owned systemd wrapper required' >&2; exit 1; }
(( $# == 1 )) || { echo 'usage: pi-systemd-class.sh CLASS' >&2; exit 2; }

class=$1
case "$class" in
  databases|rustfs|configs|retention|deep-verify) ;;
  *) echo "unsupported backup class: $class" >&2; exit 2 ;;
esac

env_file=/ssd-data/infra/backup/runner.env
app_root=/ssd-data/infra/backup-runner/app
set -a
# shellcheck disable=SC1091
source "$env_file"
set +a

cpu_quota=${BACKUP_PI_CPU_QUOTA:-100%}
memory_max=${BACKUP_PI_MEMORY_MAX:-1G}
io_weight=${BACKUP_PI_IO_WEIGHT:-50}
[[ "$cpu_quota" =~ ^[0-9]+%$ ]] || { echo 'invalid BACKUP_PI_CPU_QUOTA' >&2; exit 2; }
[[ "$memory_max" =~ ^[0-9]+([KMG]i?B?)?$ ]] || { echo 'invalid BACKUP_PI_MEMORY_MAX' >&2; exit 2; }
[[ "$io_weight" =~ ^[1-9][0-9]*$ ]] || { echo 'invalid BACKUP_PI_IO_WEIGHT' >&2; exit 2; }

scope=(systemd-run --scope --quiet -p "CPUQuota=$cpu_quota" -p "MemoryMax=$memory_max" -p "IOWeight=$io_weight")
case "$class" in
  databases|rustfs)
    run_id="${class}-$(date -u +%Y%m%d-%H%M%S)"
    exec "${scope[@]}" -- /bin/bash "$app_root/automation/backup-runner/run-class.sh" "$class" "$run_id"
    ;;
  configs)
    exec "${scope[@]}" -- /bin/bash "$app_root/automation/backup-runner/export-configs-pi.sh"
    ;;
  retention)
    exec "${scope[@]}" -- /bin/bash "$app_root/automation/backup-runner/run-retention.sh"
    ;;
  deep-verify)
    exec "${scope[@]}" -- /usr/bin/flock -n "${BACKUP_LOCK_FILE:-/ssd-data/infra/backups/homelab/.homelab-backup.lock}" \
      /bin/bash -c 'for deep_class in databases rustfs; do bash "$1/backup/scripts/run-integrity-check.sh" "$deep_class"; done' -- "$app_root"
    ;;
esac
