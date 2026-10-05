#!/usr/bin/env bash
set -euo pipefail

: "${RESTIC_PASSWORD_FILE:?RESTIC_PASSWORD_FILE is required}"
: "${RCLONE_CONFIG_FILE:?RCLONE_CONFIG_FILE is required}"
: "${BACKUP_LOCAL_RCLONE_BIN:?BACKUP_LOCAL_RCLONE_BIN is required}"

RESTIC_IMAGE=${RESTIC_IMAGE:-restic/restic:latest}

# rclone may refresh an OAuth token during a Drive operation. Keep that update
# inside a per-process working copy so the source config is never mutated or
# mounted read-only while still allowing token refresh across restic calls.
if [[ -z "${RCLONE_CONFIG_WORKDIR:-}" ]]; then
  RCLONE_CONFIG_WORKDIR=$(mktemp -d "${TMPDIR:-/tmp}/homelab-rclone.XXXXXX")
  export RCLONE_CONFIG_WORKDIR
  export RCLONE_CONFIG_WORKDIR_CREATED=1
  trap 'rm -rf -- "$RCLONE_CONFIG_WORKDIR"' EXIT
fi
cp "$RCLONE_CONFIG_FILE" "$RCLONE_CONFIG_WORKDIR/rclone.conf"
chmod 600 "$RCLONE_CONFIG_WORKDIR/rclone.conf"

restic_run() {
  local volumes=()
  if [[ -n "${RESTIC_INPUT_DIR:-}" ]]; then
    volumes+=(--volume "${RESTIC_INPUT_DIR}:/backup-run:ro")
  fi
  if [[ -n "${RESTIC_RESTORE_DIR:-}" ]]; then
    volumes+=(--volume "${RESTIC_RESTORE_DIR}:/restore-target")
  fi
  docker run --rm \
    -e RCLONE_CONFIG=/config/rclone.conf \
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
