# VM100 OpenTofu import boundary

This module is an unimported scaffold for VM100, not an approved live baseline.
Do not apply it: the Proxmox API exposed mismatches in name, protection, OS type,
disk flags and attached cloud-init media. See the
[verified preflight](../../../docs/deployments/vm100-import-preflight-2026-10-14.md).
The table below contains intended/guessed values, not a completed import:

| Field | Value |
|---|---|
| Proxmox node | `pve` |
| VM ID | `100` |
| Name | `vm100-prod` |
| LAN | `10.10.0.31` |
| vCPU / RAM | `6` / `16384 MiB` |
| Root disk | `local-lvm`, `scsi0`, `200 GiB` |
| Bridge | `vmbr0` |

The local backend is currently UNENCRYPTED and must not store production state
until encryption and key recovery are implemented and verified. Move the state to the
private RustFS S3-compatible backend only after bucket versioning, credentials,
locking, and restore have been verified. The state must remain separate from
application data and must never be committed.

## Import workflow

Run through the pinned execution image and Semaphore `tofu-plan` template:

```bash
export TF_VAR_proxmox_api_token='provided by Semaphore only'
tofu init
tofu fmt -check
tofu validate
tofu plan -out=vm100.tfplan
```

The first plan must be import-only or a reviewed zero-destroy delta. Any disk
replacement, network replacement, destroy, or unexpected VM recreation blocks
the workflow. After a Manager-approved import:

The initial import gate is stricter: it rejects every infrastructure mutation,
including in-place updates. Pipe the private JSON plan directly to the gate;
never publish raw JSON plans as CI artifacts because they can include secrets:

```bash
set -o pipefail
tofu show -json vm100.tfplan | python ../../scripts/check-vm100-plan.py --mode import
```

After the baseline is reconciled, encryption is tested, and the import is approved:

```bash
tofu apply vm100.tfplan
tofu plan -detailed-exitcode
```

The second plan must be no-op before CPU, RAM, disk, or swap policy changes are
managed. `prevent_destroy = true` is a guardrail, not a substitute for review.
