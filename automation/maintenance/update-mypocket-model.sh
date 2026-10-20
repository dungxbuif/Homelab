#!/usr/bin/env bash
set -euo pipefail

service=mypocket-worker
expected=DeepSeek-V4.1-Flash
receipt_root=${MYPOCKET_MODEL_RECEIPT_ROOT:-/var/lib/homelab-maintenance}

swarm_manager=$(docker info --format '{{.Swarm.ControlAvailable}}' 2>/dev/null || true)
if [[ "$swarm_manager" != true ]]; then
  printf 'FAIL mypocket model update requires a Swarm manager\n' >&2
  exit 2
fi

if ! docker service inspect "$service" >/dev/null 2>&1; then
  printf 'FAIL service not found: %s\n' "$service" >&2
  exit 2
fi

current=$(docker service inspect "$service" --format '{{range .Spec.TaskTemplate.ContainerSpec.Env}}{{println .}}{{end}}' |
  awk -F= '$1 == "AI_MODEL" {sub(/^[^=]*=/, ""); print; exit}')
if [[ "$current" == "$expected" ]]; then
  printf 'OK service=%s model=%s\n' "$service" "$current"
  exit 0
fi

timestamp=$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p "$receipt_root"
receipt="$receipt_root/mypocket-worker-model-$timestamp.txt"
umask 077
{
  printf 'service=%s\n' "$service"
  printf 'previous_model=%s\n' "${current:-<unset>}"
  printf 'new_model=%s\n' "$expected"
  printf 'changed_at=%s\n' "$timestamp"
} > "$receipt"

docker service update --detach=false \
  --update-order start-first \
  --env-rm AI_MODEL \
  --env-add "AI_MODEL=$expected" \
  "$service" >/dev/null

running=$(docker ps -q --filter "label=com.docker.swarm.service.name=$service" --filter status=running)
if [[ -z "$running" ]]; then
  printf 'FAIL service=%s has no running task after update\n' "$service" >&2
  exit 1
fi

observed=$(docker inspect $(printf '%s\n' "$running" | head -n1) \
  --format '{{range .Config.Env}}{{println .}}{{end}}' |
  awk -F= '$1 == "AI_MODEL" {sub(/^[^=]*=/, ""); print; exit}')
if [[ "$observed" != "$expected" ]]; then
  printf 'FAIL service=%s expected=%s observed=%s\n' "$service" "$expected" "${observed:-<unset>}" >&2
  exit 1
fi

printf 'OK service=%s model=%s receipt=%s\n' "$service" "$observed" "$receipt"
