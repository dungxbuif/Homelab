#!/bin/bash
set -euo pipefail
export PATH=/usr/sbin:/usr/bin:/sbin:/bin
set -a
# shellcheck disable=SC1091
source /etc/homelab-backup/runner.env
set +a
export BACKUP_HEALTH_EXPECTED_CLASSES='gitlab database-instances' BACKUP_HEALTH_REMOTE_PI=true
exec /bin/bash /opt/apps/homelab-backup/app/backup/scripts/check-backup-health.sh
