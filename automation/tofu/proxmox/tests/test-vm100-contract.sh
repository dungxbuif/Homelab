#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }

for file in versions.tf providers.tf main.tf variables.tf outputs.tf imports.tf README.md; do
  test -f "$root/$file" || fail "missing proxmox/$file"
done

grep -Eq 'source[[:space:]]*=[[:space:]]*"bpg/proxmox"' "$root/versions.tf" \
  || fail 'Proxmox provider must be bpg/proxmox'
grep -Eq 'version[[:space:]]*=[[:space:]]*"[0-9]+\.[0-9]+\.[0-9]+"' "$root/versions.tf" \
  || fail 'Proxmox provider must be pinned'
grep -Eq 'vm_id[[:space:]]*=[[:space:]]*var\.vm_id' "$root/main.tf" \
  || fail 'VM ID must be an explicit variable'
grep -Eq 'default[[:space:]]*=[[:space:]]*100' "$root/variables.tf" \
  || fail 'VM100 must be the default managed VM'
grep -Eq 'prevent_destroy[[:space:]]*=[[:space:]]*true' "$root/main.tf" \
  || fail 'VM100 must prevent accidental destroy'
grep -Eq 'to[[:space:]]*=[[:space:]]*proxmox_virtual_environment_vm\.vm100' "$root/imports.tf" \
  || fail 'VM100 import block is required'
if grep -RE 'k8s|kube|vmid[[:space:]]*=[[:space:]]*(101|102)' "$root" --include='*.tf' | grep -v 'homelab-k8s-iac' | grep -q .; then
  fail 'historical Kubernetes or VM101/102 target found in active module'
fi

printf 'vm100 OpenTofu contract: ok\n'
