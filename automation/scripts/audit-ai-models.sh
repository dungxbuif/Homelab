#!/usr/bin/env bash
set -euo pipefail

expected_model=${AI_EXPECTED_MODEL:-DeepSeek-V4.1-Flash}
failures=0

check_service() {
  local service=$1
  local env_key=$2
  local ids id value
  ids=$(docker ps -q --filter "name=${service}")
  if [[ -z "$ids" ]]; then
    printf 'FAIL service=%s reason=no-running-container\n' "$service"
    failures=$((failures + 1))
    return
  fi
  while IFS= read -r id; do
    [[ -n "$id" ]] || continue
    value=$(docker inspect "$id" --format '{{range .Config.Env}}{{println .}}{{end}}' |
      awk -F= -v key="$env_key" '$1 == key {sub(/^[^=]*=/, ""); print; exit}')
    if [[ "$value" == "$expected_model" ]]; then
      printf 'OK service=%s model=%s\n' "$service" "$value"
    else
      printf 'FAIL service=%s expected=%s observed=%s\n' "$service" "$expected_model" "${value:-<unset>}"
      failures=$((failures + 1))
    fi
  done <<< "$ids"
}

check_service openclaw OPENAI_MODEL
check_service whiteboard-backend AI_MODEL_FAST
check_service whiteboard-backend AI_MODEL_REASONING
check_service mypocket-api AI_MODEL
check_service mypocket-worker AI_MODEL

if ((failures > 0)); then
  printf 'AI model audit failed: %d check(s)\n' "$failures" >&2
  exit 1
fi
echo 'AI model audit passed'
