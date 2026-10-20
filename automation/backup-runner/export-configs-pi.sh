#!/usr/bin/env bash
set -euo pipefail

# Fixed allowlist for the VM100 -> Pi5 configuration archive. The archive is
# streamed to the caller; it is never written to a Pi5 staging directory.
required=(
  home/dungxbuif/edge/traefik/traefik.yml
  home/dungxbuif/edge/traefik/dynamic.yml
  home/dungxbuif/edge/adguard/conf
  home/dungxbuif/edge/rathole/rathole.toml
  ssd-data/infra/docker-compose.yml
)
optional=(
  home/dungxbuif/edge/traefik/acme.json
  home/dungxbuif/edge/adguard/work
  ssd-data/infra/couchdb/.env
  ssd-data/infra/couchdb/obsidian-sync.env
  ssd-data/infra/redis-prod/docker-compose.yml
  ssd-data/infra/redis-prod/docker-compose.override.yml
  ssd-data/infra/backup/runner.env
)

for path in "${required[@]}"; do
  [[ -e "/$path" ]] || {
    printf 'required Pi5 config source is missing: /%s\n' "$path" >&2
    exit 1
  }
done

members=("${required[@]}")
for path in "${optional[@]}"; do
  [[ -e "/$path" ]] && members+=("$path")
done

# AdGuard keeps its active YAML root-owned and mode 0600. Do not weaken that
# permission just for backup. A local, network-disabled helper container reads
# the explicit allowlist as root and streams it directly to the caller; no
# Docker socket is mounted and no Pi-side staging copy is created.
command -v docker >/dev/null 2>&1 || {
  echo 'docker is required to read root-owned allowlisted config sources' >&2
  exit 1
}
docker run --rm --network none --user 0:0 \
  --volume /home/dungxbuif/edge:/home/dungxbuif/edge:ro \
  --volume /ssd-data/infra:/ssd-data/infra:ro \
  alpine:3.22 \
  tar -C / -cf - "${members[@]}"
