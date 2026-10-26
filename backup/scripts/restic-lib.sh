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
  rclone_prepare_args=("$RCLONE_CONFIG_FILE")
  if [[ -n "${RCLONE_CONFIG_WORK_ROOT:-}" ]]; then
    rclone_prepare_args+=(--root "$RCLONE_CONFIG_WORK_ROOT")
  elif [[ -n "${BACKUP_STAGING_ROOT:-}" ]]; then
    rclone_prepare_args+=(--root "$BACKUP_STAGING_ROOT/.runtime/rclone")
  fi
  RCLONE_CONFIG_WORKDIR=$(python3 "$rclone_prepare_script" "${rclone_prepare_args[@]}")
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
  # Drive's default 10s pacer made even small uploads hold the global lock for
  # minutes. Keep requests serialized, but use a short delay and allow an
  # explicit override for quota-sensitive operations.
  local drive_pacer_min_sleep=${RCLONE_DRIVE_PACER_MIN_SLEEP:-100ms}
  local drive_pacer_burst=${RCLONE_DRIVE_PACER_BURST:-1}
  # rclone uses its own SizeSuffix grammar; `Mi` is a Kubernetes-style unit
  # and is rejected by rclone. Keep the equivalent decimal value explicit.
  local drive_chunk_size=${RCLONE_DRIVE_CHUNK_SIZE:-64M}
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
  if [[ -n "${RESTIC_LOCAL_REPOSITORY_DIR:-}" ]]; then
    volumes+=(--volume "${RESTIC_LOCAL_REPOSITORY_DIR}:/restic-repo")
  fi
  if [[ -n "${RESTIC_CONTAINER_USER:-}" ]]; then
    volumes+=(--user "$RESTIC_CONTAINER_USER")
  fi
  # Debian/Ubuntu packages ship a dynamically linked rclone binary, while the
  # pinned Restic image is intentionally minimal. Mount only the two runtime
  # objects needed by that binary when the host explicitly provides them.
  if [[ -n "${RCLONE_DYNAMIC_LINKER:-}" ]]; then
    volumes+=(--volume "$RCLONE_DYNAMIC_LINKER:/lib64/ld-linux-x86-64.so.2:ro")
  fi
  if [[ -n "${RCLONE_LIBC:-}" ]]; then
    volumes+=(--volume "$RCLONE_LIBC:/lib/x86_64-linux-gnu/libc.so.6:ro")
  fi
  local restic_lifecycle_args=(--timeout "$restic_command_timeout")
  if [[ "${RESTIC_INTERACTIVE_STDIN:-false}" == true ]]; then
    restic_lifecycle_args+=(--interactive-stdin)
  fi
  python3 "$(dirname -- "$rclone_prepare_script")/run_restic_container.py" \
    "${restic_lifecycle_args[@]}" -- \
    -e RCLONE_CONFIG=/config/rclone.conf \
    -e RCLONE_DRIVE_PACER_MIN_SLEEP="$drive_pacer_min_sleep" \
    -e RCLONE_DRIVE_PACER_BURST="$drive_pacer_burst" \
    -e RCLONE_DRIVE_CHUNK_SIZE="$drive_chunk_size" \
    -e RCLONE_LOW_LEVEL_RETRIES="$low_level_retries" \
    -e RCLONE_RETRIES="$retries" \
    -e RCLONE_RETRIES_SLEEP="$retries_sleep" \
    -e RCLONE_TIMEOUT="$rclone_timeout" \
    -e RCLONE_CONNECT_TIMEOUT="$rclone_connect_timeout" \
    -e HOME=/tmp \
    -e RESTIC_CACHE_DIR=/tmp/restic-cache \
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
    databases|database-instances|rustfs|gitlab|configs) printf 'rclone:%s:%s/%s' "${RCLONE_REMOTE:?}" "${DRIVE_ROOT:?}" "$class" ;;
    *) echo "unsupported backup class: $class" >&2; return 2 ;;
  esac
}
