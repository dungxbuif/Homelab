#!/usr/bin/env bash
set -euo pipefail

root=$(cd -- "$(dirname -- "$0")/../.." && pwd)
script="$root/automation/maintenance/update-mypocket-model.sh"

grep -q 'Swarm manager' "$script"
grep -q '^service=mypocket-worker$' "$script"
grep -q '^expected=DeepSeek-V4.1-Flash$' "$script"
grep -q -- '--env-rm AI_MODEL' "$script"
grep -q -- '--env-add "AI_MODEL=' "$script"
grep -q 'start-first' "$script"
if grep -Eq 'docker service update.*\$\{[^}]*SERVICE' "$script"; then
  echo 'model update must not allow arbitrary service interpolation' >&2
  exit 1
fi

echo 'mypocket model update contract tests passed'
