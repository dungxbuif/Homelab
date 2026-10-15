#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
staging_root=${BACKUP_STAGING_ROOT:-/opt/apps/homelab-backup/runs}
status_root=${BACKUP_STATUS_ROOT:-$staging_root/.state}
lock_file=${BACKUP_LOCK_FILE:-/run/lock/homelab-backup.lock}
expected_classes=${BACKUP_HEALTH_EXPECTED_CLASSES:-gitlab}
incomplete_age=${BACKUP_INCOMPLETE_MAX_AGE_SECONDS:-604800}
marker_max_age=${BACKUP_RETENTION_MAX_AGE_SECONDS:-93600}
active_max_age=${BACKUP_HEALTH_ACTIVE_MAX_AGE_SECONDS:-21600}
min_free_bytes=${BACKUP_HEALTH_MIN_FREE_BYTES:-10737418240}
now=$(date -u +%s)
notify=false
[[ "${1:-}" == --notify ]] && notify=true

problems=()
warnings=()
details=()

if [[ "${BACKUP_HEALTH_CHECK_UNITS:-true}" == true ]] && command -v systemctl >/dev/null 2>&1; then
  for unit in homelab-backup@databases.service homelab-backup@database-instances.service homelab-backup@gitlab.service homelab-backup@rustfs.service homelab-backup@retention.service; do
    state=$(systemctl is-failed "$unit" 2>/dev/null || true)
    [[ "$state" == failed ]] && problems+=("failed unit: $unit")

    # A oneshot backup is normally inactive after completion. If it stays
    # active or activating for too long, report it before systemd's hard
    # timeout kills the process. The check is advisory because large exports
    # can legitimately run for several hours.
    unit_state=$(systemctl show "$unit" -p ActiveState --value 2>/dev/null || true)
    if [[ "$unit_state" == active || "$unit_state" == activating ]]; then
      started_us=$(systemctl show "$unit" -p ExecMainStartTimestampMonotonic --value 2>/dev/null || true)
      uptime_value=$(awk '{print int($1)}' "${BACKUP_HEALTH_UPTIME_FILE:-/proc/uptime}" 2>/dev/null || true)
      if [[ "$started_us" =~ ^[0-9]+$ && "$uptime_value" =~ ^[0-9]+$ ]] && ((started_us > 0)); then
        runtime=$((uptime_value - started_us / 1000000))
        if ((runtime < 0)); then
          warnings+=("invalid monotonic start time: $unit")
        elif ((runtime > active_max_age)); then
          warnings+=("overlong unit: $unit runtime=${runtime}s")
        fi
        details+=("$unit state=$unit_state runtime=${runtime}s")
      else
        warnings+=("active unit has no valid monotonic start time: $unit")
      fi
    fi
  done
fi

if [[ -d "$staging_root" ]]; then
  while IFS= read -r run_dir; do
    [[ -n "$run_dir" ]] || continue
    warnings+=("old incomplete run: $run_dir")
  done < <(find "$staging_root" -maxdepth 1 -type d -name '.*.incomplete' -mmin "+$((incomplete_age / 60))" -print 2>/dev/null)
else
  warnings+=("staging root is missing: $staging_root")
fi

if [[ -d "$staging_root" ]]; then
  read -r available_kb < <(df -Pk "$staging_root" | awk 'NR == 2 {print $4}')
  if [[ "$available_kb" =~ ^[0-9]+$ ]]; then
    available_bytes=$((available_kb * 1024))
    details+=("free_bytes=$available_bytes")
    ((available_bytes >= min_free_bytes)) || problems+=("low free space: ${available_bytes} bytes")
  else
    problems+=("could not read free space for: $staging_root")
  fi
fi

if [[ "${BACKUP_HEALTH_SKIP_LOCK:-false}" == true ]]; then
  details+=("backup_lock=skipped")
elif ! command -v flock >/dev/null 2>&1; then
  warnings+=("flock command unavailable; lock state not verified")
else
  mkdir -p "$(dirname -- "$lock_file")"
  exec 9>"$lock_file"
  if ! flock -n 9; then
    warnings+=("backup lock is currently held by another process")
  else
    details+=("backup_lock=free")
  fi
fi

for class in $expected_classes; do
  marker="$status_root/$class.success"
  if [[ ! -f "$marker" ]]; then
    warnings+=("missing success marker: $class")
  else
    completed_at=$(sed -n 's/^completed_at=//p' "$marker")
    if [[ "$completed_at" =~ ^[0-9]+$ ]]; then
      age=$((now - completed_at))
      if ((age < 0 || age > marker_max_age)); then
        warnings+=("stale success marker: $class age=${age}s")
      else
        details+=("$class.success_age=${age}s")
      fi
    else
      problems+=("invalid success marker: $marker")
    fi
  fi
done

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

if [[ "$notify" == true && "$status" != success ]]; then
  notify_script=${BACKUP_NOTIFY_SCRIPT:-$script_dir/notify-mezon.sh}
  detail_text=$(printf '%s\n' "${problems[@]-}" "${warnings[@]-}" "${details[@]-}" | sed '/^$/d')
  detail_text=${detail_text:0:2400}
  bash "$notify_script" --kind health --status "$status" --summary "$summary" --details "$detail_text"
fi

[[ "$status" == success ]]
