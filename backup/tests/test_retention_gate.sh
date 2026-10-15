#!/usr/bin/env bash
set -euo pipefail

root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

mkdir -p "$tmp/app/backup/scripts" "$tmp/status" "$tmp/bin"
cat > "$tmp/bin/flock" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
chmod 0755 "$tmp/bin/flock"
cat > "$tmp/app/backup/scripts/verify-retention.sh" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$1" >> "${RETENTION_CALL_LOG:?}"
EOF
chmod 0755 "$tmp/app/backup/scripts/verify-retention.sh"
cat > "$tmp/app/backup/scripts/cleanup-local-runs.sh" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$1" >> "${CLEANUP_CALL_LOG:?}"
EOF
chmod 0755 "$tmp/app/backup/scripts/cleanup-local-runs.sh"

common_env=(
  BACKUP_APP_ROOT="$tmp/app"
  BACKUP_STATUS_ROOT="$tmp/status"
  RESTIC_PASSWORD_FILE="$tmp/password"
  RCLONE_CONFIG_FILE="$tmp/rclone.conf"
  BACKUP_LOCAL_RCLONE_BIN="$tmp/rclone"
  RCLONE_REMOTE=gdrive
  DRIVE_ROOT=homelab-backups
  BACKUP_LOCK_FILE="$tmp/lock"
  PATH="$tmp/bin:$PATH"
  RETENTION_CALL_LOG="$tmp/calls"
  CLEANUP_CALL_LOG="$tmp/cleanup-calls"
)
touch "$tmp/password" "$tmp/rclone.conf" "$tmp/rclone"

if env "${common_env[@]}" bash "$root/scripts/../scripts/../../automation/backup-runner/run-retention.sh"; then
  echo 'retention must refuse without recent class success markers' >&2
  exit 1
fi
test ! -e "$tmp/calls"

now=$(date +%s)
for class in databases rustfs gitlab; do
  printf 'status=success\ncompleted_at=%s\n' "$now" > "$tmp/status/$class.success"
done
env "${common_env[@]}" bash "$root/../automation/backup-runner/run-retention.sh"
test "$(sort "$tmp/calls")" = $'databases\ngitlab\nrustfs'
test "$(sort "$tmp/cleanup-calls")" = $'databases\ngitlab\nrustfs'

echo 'retention gate tests passed'
