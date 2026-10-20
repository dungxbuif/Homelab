# VM100 vzdump preflight: 2026-10-21

## Proxmox evidence

Read-only Proxmox API (`pve` / `10.10.0.20`, version 8.3.5) reports:

| Item | Current value |
|---|---|
| VM | `100`, running, 6 vCPU, 16 GiB RAM |
| Disk | `local-lvm:vm-100-disk-0`, 200 GiB |
| `local` directory storage | 89.8 GB free, backup content enabled |
| `local-lvm` | 100.0 GB free, 73.3% thin-pool usage |
| VM snapshots | `pre-docker-ce-20261014` plus the live `current` state |
| PBS/NAS storage | Not configured |

The host has enough `local` space for a compressed first copy only if the
compressed guest image stays below the remaining 89.8 GB. That copy would
still share the Proxmox host and is not protection against host/storage loss.
The VM's 200 GiB logical disk must not be used as the sizing estimate for a
compressed archive without measuring the actual archive.

## Decision

Do not start a production `vzdump` yet. B3 needs a separate failure domain:
Proxmox Backup Server, NAS, or an attached backup disk mounted as a dedicated
Proxmox storage. Once that target exists, run a snapshot-mode, zstd-compressed
backup, verify the task log and archive size, and perform a file-level restore
test before calling B3 complete.

The existing `pre-docker-ce-20261014` snapshot remains a rollback point for
the VM state, not a backup substitute. It is not deleted or modified by this
preflight.
