#!/usr/bin/env bash
set -euo pipefail

root=$(cd -- "$(dirname -- "$0")/../.." && pwd)
script="$root/automation/maintenance/docker-maintenance.sh"

grep -q 'DOCKER_DF_TIMEOUT_SECONDS' "$script"
grep -q 'timeout.*docker system df' "$script"
grep -q 'docker accounting skipped' "$script"

echo 'docker maintenance contract tests passed'
