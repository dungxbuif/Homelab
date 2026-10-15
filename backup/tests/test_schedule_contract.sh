#!/usr/bin/env bash
set -euo pipefail

root=$(cd -- "$(dirname -- "$0")/../.." && pwd)
schedule="$root/automation/backup-runner/schedule.yaml"
grep -q 'timezone: Asia/Ho_Chi_Minh' "$schedule"
grep -q '0 1 \* \* \*' "$schedule"
grep -q '30 2 \* \* \*' "$schedule"
grep -q '30 4 \* \* \*' "$schedule"
grep -q '30 5 \* \* \*' "$schedule"
grep -q 'run-class.sh databases' "$schedule"
grep -q 'run-class.sh database-instances' "$schedule"
grep -q 'run-class.sh gitlab' "$schedule"
grep -q 'run-class.sh rustfs' "$schedule"
grep -q 'run-retention.sh' "$schedule"
echo 'schedule contract tests passed'
