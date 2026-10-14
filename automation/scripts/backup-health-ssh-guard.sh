#!/bin/bash
set -euo pipefail
if [[ "${SSH_ORIGINAL_COMMAND:-}" != backup-health ]]; then
  echo 'Only backup-health is allowed' >&2
  exit 2
fi
exec /usr/bin/sudo -n -u ubuntu /usr/local/libexec/homelab-backup-health
