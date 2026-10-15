#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
module="$script_dir/../tofu/proxmox"
umask 077
work=$(mktemp -d "${TMPDIR:-/tmp}/homelab-tofu-validate.XXXXXXXX")
trap 'rm -rf -- "$work"' EXIT
# Copy source and lock only, never operator state, cached providers or tfvars.
cp -- "$module"/*.tf "$module/.terraform.lock.hcl" "$work/"
unset TF_DATA_DIR TF_CLI_ARGS TF_CLI_ARGS_init TF_CLI_ARGS_validate
export TF_INPUT=0 TF_IN_AUTOMATION=1
cd -- "$work"
timeout "${TOFU_INIT_TIMEOUT:-10m}" tofu init -backend=false -lockfile=readonly -input=false -no-color
timeout "${TOFU_VALIDATE_TIMEOUT:-2m}" tofu validate -no-color
