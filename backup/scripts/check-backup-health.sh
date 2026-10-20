#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
staging_root=${BACKUP_STAGING_ROOT:-/opt/apps/homelab-backup/runs}
status_root=${BACKUP_STATUS_ROOT:-$staging_root/.state}
lock_file=${BACKUP_LOCK_FILE:-/run/lock/homelab-backup.lock}
expected_classes=${BACKUP_HEALTH_EXPECTED_CLASSES:-gitlab}
incomplete_age=${BACKUP_INCOMPLETE_MAX_AGE_SECONDS:-604800}
marker_max_age=${BACKUP_RETENTION_MAX_AGE_SECONDS:-93600}
restore_drill_max_age=${BACKUP_HEALTH_RESTORE_DRILL_MAX_AGE_SECONDS:-2678400}
active_max_age=${BACKUP_HEALTH_ACTIVE_MAX_AGE_SECONDS:-21600}
min_free_bytes=${BACKUP_HEALTH_MIN_FREE_BYTES:-10737418240}
disk_warn_percent=${BACKUP_HEALTH_DISK_WARN_PERCENT:-85}
disk_fail_percent=${BACKUP_HEALTH_DISK_FAIL_PERCENT:-92}
now=$(date -u +%s)
notify=false
[[ "${1:-}" == --notify ]] && notify=true

active_limit_for() {
  case "$1" in
    databases) printf '%s' "${BACKUP_HEALTH_DATABASES_MAX_AGE_SECONDS:-7200}" ;;
    database-instances) printf '%s' "${BACKUP_HEALTH_DATABASE_INSTANCES_MAX_AGE_SECONDS:-1800}" ;;
    gitlab) printf '%s' "${BACKUP_HEALTH_GITLAB_MAX_AGE_SECONDS:-18000}" ;;
    rustfs) printf '%s' "${BACKUP_HEALTH_RUSTFS_MAX_AGE_SECONDS:-5400}" ;;
    configs) printf '%s' "${BACKUP_HEALTH_CONFIGS_MAX_AGE_SECONDS:-5400}" ;;
    retention) printf '%s' "${BACKUP_HEALTH_RETENTION_MAX_AGE_SECONDS:-5400}" ;;
    *) printf '%s' "$active_max_age" ;;
  esac
}

problems=()
warnings=()
details=()
active_unit_found=false
active_remote_process_found=false

if [[ "${BACKUP_HEALTH_CHECK_UNITS:-true}" == true ]] && command -v systemctl >/dev/null 2>&1; then
  for unit in homelab-backup@databases.service homelab-backup@database-instances.service homelab-backup@gitlab.service homelab-backup@rustfs.service homelab-backup@configs.service homelab-backup@retention.service; do
    state=$(systemctl is-failed "$unit" 2>/dev/null || true)
    [[ "$state" == failed ]] && problems+=("failed unit: $unit")

    # A oneshot backup is normally inactive after completion. If it stays
    # active or activating for too long, report it before systemd's hard
    # timeout kills the process. The check is advisory because large exports
    # can legitimately run for several hours.
    unit_state=$(systemctl show "$unit" -p ActiveState --value 2>/dev/null || true)
    if [[ "$unit_state" == active || "$unit_state" == activating ]]; then
      active_unit_found=true
      class=${unit#homelab-backup@}
      class=${class%.service}
      class_limit=$(active_limit_for "$class")
      started_us=$(systemctl show "$unit" -p ExecMainStartTimestampMonotonic --value 2>/dev/null || true)
      uptime_value=$(awk '{print int($1)}' "${BACKUP_HEALTH_UPTIME_FILE:-/proc/uptime}" 2>/dev/null || true)
      if [[ "$started_us" =~ ^[0-9]+$ && "$uptime_value" =~ ^[0-9]+$ ]] && ((started_us > 0)); then
        runtime=$((uptime_value - started_us / 1000000))
        if ((runtime < 0)); then
          problems+=("invalid monotonic start time: $unit")
        elif ((runtime > class_limit)); then
          problems+=("overlong unit: $unit runtime=${runtime}s limit=${class_limit}s")
        fi
        details+=("$unit state=running runtime=${runtime}s limit=${class_limit}s")
      else
        problems+=("active unit has no valid monotonic start time: $unit")
      fi
    fi
  done
fi

if [[ -n "${BACKUP_HEALTH_ACTIVE_PROCESS_PATTERN:-}" ]] && command -v pgrep >/dev/null 2>&1; then
  if pgrep -f -- "$BACKUP_HEALTH_ACTIVE_PROCESS_PATTERN" >/dev/null 2>&1; then
    active_remote_process_found=true
    details+=("backup_process=active_remote_runner")
  fi
fi

active_remote_class() {
  local class=$1
  [[ -n "${BACKUP_HEALTH_ACTIVE_PROCESS_PATTERN:-}" ]] || return 1
  pgrep -f -- "${BACKUP_HEALTH_ACTIVE_PROCESS_PATTERN}.*[[:space:]]${class}([[:space:]]|$)" >/dev/null 2>&1
}

active_local_class() {
  local class=$1
  command -v systemctl >/dev/null 2>&1 || return 1
  local state
  state=$(systemctl show "homelab-backup@${class}.service" -p ActiveState --value 2>/dev/null || true)
  [[ "$state" == active || "$state" == activating ]]
}

if [[ -d "$staging_root" ]]; then
  while IFS= read -r run_dir; do
    [[ -n "$run_dir" ]] || continue
    warnings+=("old incomplete run: $run_dir")
  done < <(find "$staging_root" -maxdepth 1 -type d -name '.*.incomplete' -mmin "+$((incomplete_age / 60))" -print 2>/dev/null)
else
  warnings+=("staging root is missing: $staging_root")
fi

if [[ -d "$staging_root" ]]; then
  read -r total_kb used_kb available_kb < <(df -Pk "$staging_root" | awk 'NR > 1 && $2 ~ /^[0-9]+$/ && $3 ~ /^[0-9]+$/ && $4 ~ /^[0-9]+$/ {print $2, $3, $4; exit}')
  if [[ "$total_kb" =~ ^[0-9]+$ && "$used_kb" =~ ^[0-9]+$ && "$available_kb" =~ ^[0-9]+$ ]]; then
    available_bytes=$((available_kb * 1024))
    used_percent=$((used_kb * 100 / total_kb))
    details+=("free_bytes=$available_bytes")
    details+=("disk_used_percent=$used_percent")
    ((available_bytes >= min_free_bytes)) || problems+=("low free space: ${available_bytes} bytes")
    if ((used_percent >= disk_fail_percent)); then
      problems+=("disk usage is ${used_percent}% (failure threshold ${disk_fail_percent}%)")
    elif ((used_percent >= disk_warn_percent)); then
      warnings+=("disk usage is ${used_percent}% (warning threshold ${disk_warn_percent}%)")
    fi
  else
    problems+=("could not read free space for: $staging_root")
  fi
fi

if [[ "${BACKUP_HEALTH_SKIP_LOCK:-false}" == true ]]; then
  details+=("backup_lock=skipped")
elif ! command -v flock >/dev/null 2>&1; then
  warnings+=("flock command unavailable; lock state not verified")
else
  # Open an existing lock read-only. On systems with fs.protected_regular,
  # root cannot truncate a regular file owned by the backup service in sticky
  # /run/lock, even though it can safely flock that file.
  if [[ ! -e "$lock_file" ]]; then
    mkdir -p "$(dirname -- "$lock_file")"
    (set -o noclobber; umask 077; : >"$lock_file") || [[ -f "$lock_file" ]]
  fi
  exec 9<"$lock_file"
  if ! flock -n 9; then
    if [[ "$active_unit_found" == true || "$active_remote_process_found" == true ]]; then
      details+=("backup_lock=held_by_active_backup")
    else
      problems+=("backup lock is held without an active backup unit")
    fi
  else
    details+=("backup_lock=free")
  fi
fi

for class in $expected_classes; do
  marker="$status_root/$class.success"
  if [[ ! -f "$marker" ]]; then
    if active_remote_class "$class" || active_local_class "$class"; then
      details+=("$class.success=deferred_active")
    else
      warnings+=("missing success marker: $class")
    fi
  else
    completed_at=$(sed -n 's/^completed_at=//p' "$marker")
    if [[ "$completed_at" =~ ^[0-9]+$ ]]; then
      age=$((now - completed_at))
      if ((age < 0 || age > marker_max_age)) && (active_remote_class "$class" || active_local_class "$class"); then
        details+=("$class.success=deferred_active age=${age}s")
      elif ((age < 0 || age > marker_max_age)); then
        warnings+=("stale success marker: $class age=${age}s")
      else
        details+=("$class.success_age=${age}s")
      fi
    else
      problems+=("invalid success marker: $marker")
    fi
  fi
done

restore_drill_marker="$status_root/restore-drill.success"
if [[ ! -f "$restore_drill_marker" ]]; then
  warnings+=("missing success marker: restore-drill")
else
  completed_at=$(sed -n 's/^completed_at=//p' "$restore_drill_marker")
  if [[ "$completed_at" =~ ^[0-9]+$ ]]; then
    age=$((now - completed_at))
    if ((age < 0 || age > restore_drill_max_age)); then
      warnings+=("stale success marker: restore-drill age=${age}s")
    else
      details+=("restore-drill.success_age=${age}s")
    fi
  else
    problems+=("invalid success marker: $restore_drill_marker")
  fi
fi

if [[ "${BACKUP_HEALTH_REMOTE_PI:-false}" == true ]]; then
  remote_script=${BACKUP_HEALTH_REMOTE_SCRIPT:-$script_dir/../../automation/backup-runner/run-vm100-scheduled.sh}
  if remote_output=$(bash "$remote_script" health 2>&1); then
    details+=("Pi backup health check passed" "$remote_output")
  else
    problems+=("Pi backup health check failed" "$remote_output")
  fi
fi

status=success
summary='backup health check passed'
if ((${#problems[@]} > 0)); then
  status=failure
  summary='backup health check found failures'
elif ((${#warnings[@]} > 0)); then
  status=warning
  summary='backup health check found warnings'
fi

printf '[backup-health] %s\n' "$summary"
printf '%s\n' "${problems[@]-}" "${warnings[@]-}" "${details[@]-}" | sed '/^$/d' | sed 's/^/[backup-health] /'

if [[ "$notify" == true && ( "$status" != success || "${BACKUP_HEALTH_NOTIFY_SUCCESS:-false}" == true ) ]]; then
  notify_script=${BACKUP_NOTIFY_SCRIPT:-$script_dir/notify-mezon.sh}
  detail_text=$(printf '%s\n' "${problems[@]-}" "${warnings[@]-}" "${details[@]-}" | sed '/^$/d')
  detail_text=${detail_text:0:2400}
  if [[ "$status" == success ]]; then
    summary='daily backup health passed'
  fi
  bash "$notify_script" --kind health --status "$status" --summary "$summary" --details "$detail_text"
fi

[[ "$status" != failure ]]
