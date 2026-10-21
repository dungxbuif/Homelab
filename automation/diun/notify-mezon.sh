#!/bin/sh
set -eu

webhook_file=${MEZON_WEBHOOK_FILE:-/run/secrets/mezon-webhook}
[ -r "$webhook_file" ] || exit 1
webhook=$(cat "$webhook_file")
[ -n "$webhook" ] || exit 1

image=${DIUN_ENTRY_IMAGE:-unknown}
status=${DIUN_ENTRY_STATUS:-unknown}
digest=${DIUN_ENTRY_DIGEST:-unknown}
provider=${DIUN_ENTRY_PROVIDER:-unknown}
host=${DIUN_HOSTNAME:-unknown}

# Diun supplies registry-safe values here. Keep the payload deliberately small
# and use the same hook envelope as the homelab backup notifier.
text="[HOMELAB IMAGE WATCH] [WARN] image update available: ${image}\nprovider=${provider} status=${status} host=${host}\ndigest=${digest}"
payload=$(printf '{"type":"hook","message":{"t":"%s","mk":[{"type":"pre","s":0,"e":%s}],"mentions":[],"images":[],"hg":[]}}' \
  "$text" "${#text}")

wget -q -O /dev/null \
  --header='Content-Type: application/json' \
  --post-data="$payload" \
  "$webhook"
