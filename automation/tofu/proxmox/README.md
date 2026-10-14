# VM100 OpenTofu import boundary

This module manages only the existing production VM100 object:

| Field | Value |
|---|---|
| Proxmox node | `pve` |
| VM ID | `100` |
| Name | `vm100-prod` |
| LAN | `10.10.0.31` |
| vCPU / RAM | `6` / `16384 MiB` |
| Root disk | `local-lvm`, `scsi0`, `200 GiB` |
| Bridge | `vmbr0` |

The local backend is intentional for the import phase. Move the state to the
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

```bash
tofu apply vm100.tfplan
tofu plan -detailed-exitcode
```

The second plan must be no-op before CPU, RAM, disk, or swap policy changes are
managed. `prevent_destroy = true` is a guardrail, not a substitute for review.
