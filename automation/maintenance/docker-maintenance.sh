#!/usr/bin/env bash
set -euo pipefail

lock_file=/run/lock/homelab-backup.lock
if [[ ! -e "$lock_file" ]]; then
  (set -o noclobber; umask 077; : > "$lock_file") || [[ -f "$lock_file" ]]
fi
# Open existing lock read-only: root O_CREAT is blocked for another user's
# file in sticky /run/lock on systems using fs.protected_regular.
exec 9<"$lock_file"
flock --nonblock --conflict-exit-code 75 9 || exit "$?"

df -h /
python3 /usr/local/lib/homelab-maintenance/cleanup-dead-tasks.py --apply
# Keep tagged releases available for rollback; never prune volumes.
docker image prune --force --filter until=168h
docker builder prune --force --filter until=168h --keep-storage 5GB
# Docker's accounting walk can hang when containerd has a stale layer record.
# Cleanup is still valid if that read-only report is unavailable.
docker_df_timeout=${DOCKER_DF_TIMEOUT_SECONDS:-30}
set +e
timeout --signal=TERM "$docker_df_timeout" docker system df
docker_df_status=$?
set -e
if ((docker_df_status != 0)); then
  echo "docker accounting skipped: docker system df exited with status $docker_df_status" >&2
fi
df -h /
