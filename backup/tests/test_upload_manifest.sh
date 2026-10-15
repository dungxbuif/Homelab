#!/usr/bin/env bash
set -euo pipefail

root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

mkdir -p "$tmp/run" "$tmp/bin" "$tmp/state"
printf 'artifact\n' > "$tmp/run/artifact.txt"
(cd "$tmp/run" && sha256sum artifact.txt > checksums.sha256)
printf '%s\n' '{"status":"complete","kind":"databases","run_id":"test-run","coverage":["postgresql/test"]}' > "$tmp/run/manifest.json"
touch "$tmp/run/COMPLETE"
printf 'restic-password\n' > "$tmp/restic-password"
printf '[gdrive]\ntype = local\n' > "$tmp/rclone.conf"
printf '#!/bin/sh\nexit 0\n' > "$tmp/fake-rclone"
chmod 0755 "$tmp/fake-rclone"
cat > "$tmp/bin/timeout" <<'EOF'
#!/bin/sh
set -eu
[ "$1" = --foreground ] && shift
shift
exec "$@"
EOF
chmod 0755 "$tmp/bin/timeout"
cat > "$tmp/bin/pgrep" <<'EOF'
#!/bin/sh
exit "${FAKE_PGREP_STATUS:-1}"
EOF
chmod 0755 "$tmp/bin/pgrep"

cat > "$tmp/bin/docker" <<'EOF'
#!/bin/sh
set -eu
state=${FAKE_DOCKER_STATE:?}
printf '%s\n' "$@" >> "$state/args"
[ "${1:-}" != container ] || exit 0
if [ "${1:-}" = create ]; then
  printf '%s\n' "$@" > "$state/create-args"
  printf '%064d\n' 1
  exit 0
fi
if [ "${1:-}" = start ]; then
  set --
  while IFS= read -r arg; do set -- "$@" "$arg"; done < "$state/create-args"
fi
command=''
config_file=''
for arg in "$@"; do
  case "$arg" in
    */config) config_file="${arg%:/config}/rclone.conf" ;;
  esac
done
for arg in "$@"; do
  case "$arg" in
    init|snapshots|backup|check|unlock|restore) command=$arg; break ;;
  esac
done
case "$command" in
  init)
    grep -q 'refreshed=true' "$config_file"
    touch "$state/initialized"
    ;;
  snapshots)
    if [ -f "$state/backed-up" ]; then
      printf '%s\n' '[{"id":"snap-test"}]'
    else
      printf '%s\n' 'refreshed=true' >> "$config_file"
      printf '%s\n' '[]'
      exit 1
    fi
    ;;
  backup) touch "$state/backed-up"; printf '%s\n' '{"message_type":"summary"}' ;;
  check)
    if [ "${FAKE_DOCKER_STALE_LOCK:-0}" = 1 ] && {
      [ ! -f "$state/unlocked" ] || [ "${FAKE_ALWAYS_LOCK:-0}" = 1 ];
    }; then
      printf '%s\n' 'unable to create lock in backend: repository is already locked' >&2
      exit 1
    fi
    ;;
  unlock)
    [ "${FAKE_UNLOCK_PARTIAL:-0}" = 0 ] || touch "$state/unlocked"
    [ "${FAKE_UNLOCK_FAIL:-0}" = 0 ] || exit 1
    touch "$state/unlocked"
    ;;
  *) echo "unexpected fake restic command: $command" >&2; exit 1 ;;
esac
EOF
chmod 0755 "$tmp/bin/docker"

before=$(cat "$tmp/run/manifest.json")
output=$(
  PATH="$tmp/bin:$PATH" \
  FAKE_DOCKER_STATE="$tmp/state" \
  RESTIC_PASSWORD_FILE="$tmp/restic-password" \
  RCLONE_CONFIG_FILE="$tmp/rclone.conf" \
  BACKUP_LOCAL_RCLONE_BIN="$tmp/fake-rclone" \
  RCLONE_REMOTE=gdrive \
  DRIVE_ROOT=homelab-backups \
  FAKE_DOCKER_STALE_LOCK=1 \
  RESTIC_ALLOW_INIT=true \
  bash "$root/scripts/upload-restic.sh" databases "$tmp/run" explicit-run
)

test "$output" = snap-test
test "$(cat "$tmp/run/manifest.json")" = "$before"
(cd "$tmp/run" && sha256sum --quiet -c checksums.sha256)
test "$(cat "$tmp/run/remote/snapshot-id")" = snap-test
test "$(cat "$tmp/run/remote/run-id")" = explicit-run
test -f "$tmp/state/unlocked"
grep -qx 'run_id=explicit-run' "$tmp/state/args"
for excluded in restic-backup.json restic-preflight.log restic-check.log remote; do
  grep -Fqx -- "--exclude=/backup-run/$excluded" "$tmp/state/args" || {
    echo "missing root-only operational file exclusion: $excluded" >&2
    exit 1
  }
done
if grep -q 'remote_snapshot_id' "$tmp/run/manifest.json"; then
  echo 'remote snapshot metadata must not mutate the uploaded manifest' >&2
  exit 1
fi

for scenario in active failed_recheck failed_unlock partial_unlock; do
  mkdir -p "$tmp/$scenario/run" "$tmp/$scenario/state"
  cp "$tmp/run/manifest.json" "$tmp/run/COMPLETE" "$tmp/run/artifact.txt" \
    "$tmp/run/checksums.sha256" "$tmp/$scenario/run/"
  active=1; always_lock=0; unlock_fail=0; unlock_partial=0
  case "$scenario" in
    active) active=0 ;;
    failed_recheck) always_lock=1 ;;
    failed_unlock) unlock_fail=1 ;;
    partial_unlock) unlock_fail=1; unlock_partial=1 ;;
  esac
  if PATH="$tmp/bin:$PATH" FAKE_DOCKER_STATE="$tmp/$scenario/state" \
    RESTIC_PASSWORD_FILE="$tmp/restic-password" RCLONE_CONFIG_FILE="$tmp/rclone.conf" \
    BACKUP_LOCAL_RCLONE_BIN="$tmp/fake-rclone" RCLONE_REMOTE=gdrive DRIVE_ROOT=homelab-backups \
    FAKE_DOCKER_STALE_LOCK=1 RESTIC_ALLOW_INIT=true FAKE_PGREP_STATUS="$active" \
    FAKE_ALWAYS_LOCK="$always_lock" FAKE_UNLOCK_FAIL="$unlock_fail" FAKE_UNLOCK_PARTIAL="$unlock_partial" \
    bash "$root/scripts/upload-restic.sh" databases "$tmp/$scenario/run" "$scenario" \
    >"$tmp/$scenario/output" 2>"$tmp/$scenario/error"; then
    echo "unsafe successful upload result: $scenario" >&2
    exit 1
  fi
  test ! -e "$tmp/$scenario/run/remote/snapshot-id"
  test ! -e "$tmp/$scenario/run/remote/run-id"
  unlocks=$(grep -cx unlock "$tmp/$scenario/state/args" || true)
  if [[ "$scenario" == active ]]; then
    test "$unlocks" = 0
  else
    test "$unlocks" = 1
  fi
done

echo 'upload manifest immutability test passed'
