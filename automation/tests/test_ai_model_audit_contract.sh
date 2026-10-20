#!/usr/bin/env bash
set -euo pipefail

root=$(cd -- "$(dirname -- "$0")/../.." && pwd)
script="$root/automation/scripts/audit-ai-models.sh"

grep -q 'openclaw' "$script"
grep -q 'whiteboard-backend' "$script"
grep -q 'mypocket-api' "$script"
grep -q 'mypocket-worker' "$script"
grep -q 'DeepSeek-V4.1-Flash' "$script"
if grep -Eq 'API_KEY|TOKEN|PASSWORD|SECRET' "$script"; then
  echo 'AI model audit must not print credential fields' >&2
  exit 1
fi

echo 'AI model audit contract tests passed'
