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

cat > "$tmp/bin/docker" <<'EOF'
#!/bin/sh
set -eu
state=${FAKE_DOCKER_STATE:?}
printf '%s\n' "$@" >> "$state/args"
command=''
config_file=''
for arg in "$@"; do
  case "$arg" in
    */config) config_file="${arg%:/config}/rclone.conf" ;;
  esac
done
for arg in "$@"; do
  case "$arg" in
    init|snapshots|backup|check|restore) command=$arg; break ;;
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
  check) ;;
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
  bash "$root/scripts/upload-restic.sh" databases "$tmp/run" explicit-run
)

test "$output" = snap-test
test "$(cat "$tmp/run/manifest.json")" = "$before"
(cd "$tmp/run" && sha256sum --quiet -c checksums.sha256)
test "$(cat "$tmp/run/remote/snapshot-id")" = snap-test
test "$(cat "$tmp/run/remote/run-id")" = explicit-run
grep -qx 'run_id=explicit-run' "$tmp/state/args"
if grep -q 'remote_snapshot_id' "$tmp/run/manifest.json"; then
  echo 'remote snapshot metadata must not mutate the uploaded manifest' >&2
  exit 1
fi

echo 'upload manifest immutability test passed'
