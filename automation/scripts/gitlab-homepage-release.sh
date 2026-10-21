#!/usr/bin/env bash
set -euo pipefail

root_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
: "${HOMEPAGE_IMAGE_DIGEST:?HOMEPAGE_IMAGE_DIGEST is required}"
: "${HOMELAB_HOMEPAGE_RELEASE_PRIVATE_KEY_FILE:?protected file variable is required}"
: "${HOMELAB_PI_KNOWN_HOSTS_FILE:?protected file variable is required}"
: "${CI_PIPELINE_ID:?CI_PIPELINE_ID is required}"

[[ "$HOMEPAGE_IMAGE_DIGEST" =~ ^sha256:[0-9a-f]{64}$ ]] || {
  echo 'Homepage release requires an immutable SHA256 digest' >&2
  exit 1
}
[[ -r "$HOMELAB_HOMEPAGE_RELEASE_PRIVATE_KEY_FILE" ]] || {
  echo 'Homepage release key file is not readable' >&2
  exit 1
}
[[ -r "$HOMELAB_PI_KNOWN_HOSTS_FILE" ]] || {
  echo 'Pinned Pi5 known_hosts file is not readable' >&2
  exit 1
}

PYTHON_BIN=${PYTHON_BIN:-python3} \
  "$root_dir/automation/scripts/verify-deploy.sh" \
  --service homepage --image "$HOMEPAGE_IMAGE_DIGEST" --environment production

tmp_dir=$(mktemp -d)
trap 'rm -rf "$tmp_dir"' EXIT
install -m 600 "$HOMELAB_HOMEPAGE_RELEASE_PRIVATE_KEY_FILE" "$tmp_dir/id_release"

ssh -F /dev/null \
  -o BatchMode=yes \
  -o IdentitiesOnly=yes \
  -o StrictHostKeyChecking=yes \
  -o UserKnownHostsFile="$HOMELAB_PI_KNOWN_HOSTS_FILE" \
  -o ConnectTimeout=10 \
  -i "$tmp_dir/id_release" \
  homelab-homepage-release@10.10.0.5 \
  homepage-release "$HOMEPAGE_IMAGE_DIGEST" >"$tmp_dir/receipt.json"

HOMELAB_MEZON_WEBHOOK_URL=${HOMELAB_MEZON_WEBHOOK_URL:?protected Mezon variable is required} \
  "$root_dir/automation/scripts/notify-homepage-release.py" \
  --task-id "$CI_PIPELINE_ID" <"$tmp_dir/receipt.json"

cat "$tmp_dir/receipt.json"
