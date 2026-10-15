#!/usr/bin/env bash
set -euo pipefail

: "${RESTIC_PASSWORD_FILE:?RESTIC_PASSWORD_FILE is required}"
: "${RCLONE_CONFIG_FILE:?RCLONE_CONFIG_FILE is required}"
: "${BACKUP_LOCAL_RCLONE_BIN:?BACKUP_LOCAL_RCLONE_BIN is required}"

# Keep the client reproducible across hosts. Override deliberately when testing
# a newer Restic build, then record the new digest in the deployment notes.
RESTIC_IMAGE=${RESTIC_IMAGE:-restic/restic@sha256:9940e6c7421ab3a21ee9fdc4e91596d04c792b600d31b102696c75cbf3ac4481}

# rclone may refresh an OAuth token during a Drive operation. Keep that update
# inside a per-process working copy so the source config is never mutated or
# mounted read-only while still allowing token refresh across restic calls.
rclone_prepare_script=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/prepare_rclone_workdir.py
if [[ -z "${RCLONE_CONFIG_WORKDIR:-}" ]]; then
  # systemd may isolate /tmp with PrivateTmp=yes. Docker's daemon cannot see
  # that namespace, so keep the bind-mounted config under a shared path.
  rclone_work_args=()
  if [[ -n "${RCLONE_CONFIG_WORK_ROOT:-}" ]]; then
    rclone_work_args=(--root "$RCLONE_CONFIG_WORK_ROOT")
  elif [[ -n "${BACKUP_STAGING_ROOT:-}" ]]; then
    rclone_work_args=(--root "$BACKUP_STAGING_ROOT/.runtime/rclone")
  fi
  RCLONE_CONFIG_WORKDIR=$(python3 "$rclone_prepare_script" "$RCLONE_CONFIG_FILE" "${rclone_work_args[@]}")
  export RCLONE_CONFIG_WORKDIR
  export RCLONE_CONFIG_WORKDIR_CREATED=1
  trap 'rm -rf -- "$RCLONE_CONFIG_WORKDIR"' EXIT
else
  RCLONE_CONFIG_WORKDIR=$(python3 "$rclone_prepare_script" "$RCLONE_CONFIG_FILE" --existing "$RCLONE_CONFIG_WORKDIR")
fi

restic_run() {
  local volumes=()
  # Drive uses a project quota measured in API units, not only file bytes.
  # Keep requests deliberately serialized so a large repository cannot burst
  # into the shared/default project quota.
  local drive_pacer_min_sleep=${RCLONE_DRIVE_PACER_MIN_SLEEP:-10s}
  local drive_pacer_burst=${RCLONE_DRIVE_PACER_BURST:-1}
  local drive_chunk_size=${RCLONE_DRIVE_CHUNK_SIZE:-64Mi}
  local low_level_retries=${RCLONE_LOW_LEVEL_RETRIES:-10}
  local retries=${RCLONE_RETRIES:-10}
  local retries_sleep=${RCLONE_RETRIES_SLEEP:-30s}
  local rclone_timeout=${RCLONE_TIMEOUT:-15m}
  local rclone_connect_timeout=${RCLONE_CONNECT_TIMEOUT:-30s}
  # Large CouchDB exports can take longer than two hours over a paced Drive
  # remote. Keep this below the systemd service timeout so the runner can
  # finish cleanly instead of being killed mid-repository operation.
  local restic_command_timeout=${RESTIC_COMMAND_TIMEOUT:-4h}
  if [[ -n "${RESTIC_INPUT_DIR:-}" ]]; then
    volumes+=(--volume "${RESTIC_INPUT_DIR}:/backup-run:ro")
  fi
  if [[ -n "${RESTIC_RESTORE_DIR:-}" ]]; then
    volumes+=(--volume "${RESTIC_RESTORE_DIR}:/restore-target")
  fi
  python3 "$(dirname -- "$rclone_prepare_script")/run_restic_container.py" \
    --timeout "$restic_command_timeout" -- \
    -e RCLONE_CONFIG=/config/rclone.conf \
    -e RCLONE_DRIVE_PACER_MIN_SLEEP="$drive_pacer_min_sleep" \
    -e RCLONE_DRIVE_PACER_BURST="$drive_pacer_burst" \
    -e RCLONE_DRIVE_CHUNK_SIZE="$drive_chunk_size" \
    -e RCLONE_LOW_LEVEL_RETRIES="$low_level_retries" \
    -e RCLONE_RETRIES="$retries" \
    -e RCLONE_RETRIES_SLEEP="$retries_sleep" \
    -e RCLONE_TIMEOUT="$rclone_timeout" \
    -e RCLONE_CONNECT_TIMEOUT="$rclone_connect_timeout" \
    -e RESTIC_PASSWORD_FILE=/run/secrets/restic-password \
    -e RESTIC_REPOSITORY="${RESTIC_REPOSITORY:?RESTIC_REPOSITORY is required}" \
    -v "$RESTIC_PASSWORD_FILE:/run/secrets/restic-password:ro" \
    -v "$RCLONE_CONFIG_WORKDIR:/config" \
    -v "$BACKUP_LOCAL_RCLONE_BIN:/usr/local/bin/rclone:ro" \
    "${volumes[@]}" \
    "$RESTIC_IMAGE" \
    "$@"
}

restic_repo_for() {
  local class=${1:?}
  case "$class" in
    databases|rustfs|gitlab) printf 'rclone:%s:%s/%s' "${RCLONE_REMOTE:?}" "${DRIVE_ROOT:?}" "$class" ;;
    *) echo "unsupported backup class: $class" >&2; return 2 ;;
  esac
}
