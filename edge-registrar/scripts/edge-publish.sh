#!/usr/bin/env bash
# Publish one wildcard DNS hostname through Pi5 Caddy and VPS Traefik.
# Configuration is deliberately supplied through the environment, never stored here.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: edge-publish.sh --host HOST --target HOST:PORT --expose public|internal [--apply]

The command is dry-run by default. --apply writes only the live Caddyfile on
Pi5 and dynamic.yml on the VPS after showing their diffs.

Required one-time setup: place '# edge-registrar: routes' inside the existing
Pi5 wildcard Caddy site, after its proxy_protocol wrapper. The script inserts
managed route blocks immediately after this anchor and preserves the wrapper.

Environment defaults:
  PI5_HOST=dungxbuif@10.10.0.5  PI5_CADDYFILE=/ssd-data/infra/Caddyfile
  PI5_CADDY_CONTAINER=caddy    PI5_CADDY_CONTAINER_PATH=/etc/caddy/Caddyfile
  VPS_HOST=root@103.82.21.202  VPS_DYNAMIC_FILE=/root/gateway/dynamic.yml
EOF
}

HOST=""
TARGET=""
EXPOSE=""
APPLY=false
while (($#)); do
  case "$1" in
    --host) HOST="${2:-}"; shift 2 ;;
    --target) TARGET="${2:-}"; shift 2 ;;
    --expose) EXPOSE="${2:-}"; shift 2 ;;
    --apply) APPLY=true; shift ;;
    --dry-run) APPLY=false; shift ;;
    -h|--help) usage; exit 0 ;;
    *) printf 'Unknown argument: %s\n' "$1" >&2; usage >&2; exit 2 ;;
  esac
done

[[ "$HOST" =~ ^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.dungxbuif\.com$ ]] || {
  printf '%s\n' 'Host must be a lowercase non-apex *.dungxbuif.com hostname.' >&2; exit 2;
}
[[ "$TARGET" =~ ^[A-Za-z0-9._-]+:[0-9]{1,5}$ ]] || {
  printf '%s\n' 'Target must be a DNS name or IPv4 address followed by a port.' >&2; exit 2;
}
[[ "$EXPOSE" == public || "$EXPOSE" == internal ]] || {
  printf '%s\n' 'Expose must be public or internal.' >&2; exit 2;
}

PI5_HOST="${PI5_HOST:-dungxbuif@10.10.0.5}"
PI5_CADDYFILE="${PI5_CADDYFILE:-/ssd-data/infra/Caddyfile}"
PI5_CADDY_CONTAINER="${PI5_CADDY_CONTAINER:-caddy}"
PI5_CADDY_CONTAINER_PATH="${PI5_CADDY_CONTAINER_PATH:-/etc/caddy/Caddyfile}"
VPS_HOST="${VPS_HOST:-root@103.82.21.202}"
VPS_DYNAMIC_FILE="${VPS_DYNAMIC_FILE:-/root/gateway/dynamic.yml}"
NAME="${HOST//./-}"

printf 'Mode: %s\n' "$($APPLY && printf apply || printf dry-run)"
printf 'Caddy: %s -> %s\n' "$HOST" "$TARGET"

ssh "$PI5_HOST" bash -s -- "$HOST" "$TARGET" "$NAME" "$PI5_CADDYFILE" \
  "$PI5_CADDY_CONTAINER" "$PI5_CADDY_CONTAINER_PATH" "$APPLY" <<'REMOTE_CADDY'
set -euo pipefail
host=$1 target=$2 name=$3 config=$4 container=$5 container_config=$6 apply=$7
anchor='# edge-registrar: routes'
marker="# edge-registrar: $name"
route="# edge-registrar: $name
@$name host $host
handle @$name {
    reverse_proxy $target
}
"
tmp=$(mktemp "${config}.edge-registrar.XXXXXX")
cleanup() { rm -f "$tmp" "${config}.edge-registrar.bak"; }
trap cleanup EXIT
if grep -Fqx "$marker" "$config"; then
  awk -v marker="$marker" -v route="$route" '
    $0 == marker { print route; replacing=1; next }
    replacing && /^}[[:space:]]*$/ { replacing=0; next }
    !replacing { print }
  ' "$config" > "$tmp"
else
  grep -Fqx "$anchor" "$config" || {
    echo "Missing Caddy anchor '$anchor' in $config" >&2; exit 1;
  }
  awk -v anchor="$anchor" -v route="$route" '
    { print }
    $0 == anchor && !inserted { print route; inserted=1 }
  ' "$config" > "$tmp"
fi
diff -u "$config" "$tmp" || true
if [ "$apply" != true ]; then exit 0; fi
cp "$config" "${config}.edge-registrar.bak"
mv "$tmp" "$config"
if ! docker exec "$container" caddy validate --config "$container_config"; then
  mv "${config}.edge-registrar.bak" "$config"
  echo 'Caddy validation failed; restored previous configuration.' >&2
  exit 1
fi
if ! docker exec "$container" caddy reload --config "$container_config"; then
  mv "${config}.edge-registrar.bak" "$config"
  docker exec "$container" caddy reload --config "$container_config" || true
  echo 'Caddy reload failed; restored previous configuration.' >&2
  exit 1
fi
REMOTE_CADDY

if [[ "$EXPOSE" == internal ]]; then
  printf '%s\n' 'Internal route published in Caddy only; VPS Traefik was not changed.'
  exit 0
fi

printf 'Traefik SNI allow-list: %s\n' "$HOST"
ssh "$VPS_HOST" bash -s -- "$HOST" "$VPS_DYNAMIC_FILE" "$APPLY" <<'REMOTE_TRAEFIK'
set -euo pipefail
host=$1 config=$2 apply=$3
tmp=$(mktemp "${config}.edge-registrar.XXXXXX")
cleanup() { rm -f "$tmp"; }
trap cleanup EXIT
awk -v host="$host" '
  /^([[:space:]]*)rathole-passthrough:[[:space:]]*$/ { in_router=1 }
  in_router && /^[[:space:]]{4}[[:alnum:]_-]+:[[:space:]]*$/ && $0 !~ /rathole-passthrough:/ { in_router=0 }
  in_router && $0 ~ /^[[:space:]]*rule:[[:space:]]*/ {
    if (index($0, "HostSNI(`" host "`)") == 0) sub(/[[:space:]]*$/, " || HostSNI(`" host "`)")
    changed=1
  }
  { print }
  END { if (!changed) exit 42 }
' "$config" > "$tmp" || {
  status=$?
  if [ "$status" -eq 42 ]; then
    echo "Could not locate tcp.routers.rathole-passthrough.rule in $config" >&2
  fi
  exit "$status"
}
diff -u "$config" "$tmp" || true
[ "$apply" = true ] || exit 0
cp "$config" "${config}.edge-registrar.bak"
mv "$tmp" "$config"
echo 'Updated dynamic.yml. Traefik file-provider watch performs the reload.'
REMOTE_TRAEFIK

printf '%s\n' 'Completed.'
