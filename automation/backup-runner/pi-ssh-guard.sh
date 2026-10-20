#!/usr/bin/env bash
set -euo pipefail

executor=${BACKUP_PI_EXECUTOR:-/home/dungxbuif/.local/sbin/homelab-backup-executor}
command=${SSH_ORIGINAL_COMMAND:-}
case "$command" in
  "$executor databases") class=databases ;;
  "$executor rustfs") class=rustfs ;;
  "$executor configs") class=configs ;;
  "$executor retention") class=retention ;;
  "$executor deep-verify") class=deep-verify ;;
  "$executor health") class=health ;;
  *) echo 'backup SSH key accepts only the allow-listed backup classes' >&2; exit 2 ;;
esac

if [[ "$class" == retention ]]; then
  marker_root=${BACKUP_STATUS_ROOT:-/ssd-data/infra/backups/homelab/.state}
  marker_tmp="$marker_root/.gitlab.success.ssh-$$.tmp"
  mkdir -p "$marker_root"
  cat > "$marker_tmp"
  if [[ -s "$marker_tmp" ]]; then
    chmod 600 "$marker_tmp"
    mv -f "$marker_tmp" "$marker_root/gitlab.success"
  else
    rm -f "$marker_tmp"
  fi
fi

exec "$executor" "$class"
