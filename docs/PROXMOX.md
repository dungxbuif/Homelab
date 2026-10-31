---
type: Reference
title: "Proxmox Production Hypervisor"
description: "Current Proxmox host role, VMs, storage, IaC boundary and safe operations"
timestamp: 2026-10-31T00:00:00+07:00
---

# Proxmox production hypervisor

> **Not audited live on 2026-10-31.** No SSH alias or credential for Proxmox is
> recorded; agent key spraying causes `Too many authentication failures`.
> Values below come from earlier records unless marked otherwise.

## Role and guests

| Field | Value |
|---|---|
| Host | `10.10.0.20` |
| VM 100 | `vm100-prod`, `10.10.0.31`, 6 vCPU / 16 GB / 200 GiB — production compute, see [VM100](./VM100.md) |
| VM 110 | `db-ops`, `10.10.0.32` — db-management Swarm tasks only (CloudBeaver, Databasus, api/web/worker); RAM 7.8 G, disk 78 G 65 % used (live, via guest SSH) |
| Retired | VMs 101/102, Kubernetes cluster, kube-vip, Longhorn — none active; never recreate from old state |
| Storage | `local` (directory, ~89 GB free) and `local-lvm` thin pool (~77 % used) (unverified) |
| Off-host backup target | **None** (no PBS/NAS). VM110 shares VM100's failure domain. |

Database data lives on Pi5, not on Proxmox. A VM snapshot of VM100 is not a
complete application backup (GitLab data is on VM100, its DB on Pi5).

## IaC boundary

- `homelab-ops/automation/tofu/proxmox/` — import-only module for VM 100,
  `prevent_destroy = true`, SSH key comment `homelab-vm100-iac`.
- `homelab-ops/automation/tofu/proxmox-db-ops/` — VM 110.
- State is local and encrypted on the controlled runner; no remote state or
  locking yet. Proxmox API tokens come from Semaphore variables, never Git.
- No apply evidence exists. The first plan must be import-only/zero-destroy
  and the second plan a no-op before OpenTofu manages sizing. Remote state,
  templates and CI plan jobs are part of the
  [IaC rebuild plan](./superpowers/plans/2026-10-31-lab-iac-automation-rebuild.md).

## Safe operations

- Before any resize or storage cleanup: `qm config 100`, `pvesm status`, `lvs`.
  Guest free space is not proof of thin-pool headroom.
- Never run `terraform destroy` or load historical K8s-era state: it can
  reference VM IDs now used by production.
- Stop stateful workloads before destructive storage changes; reconcile disks,
  snapshots and mounts before deleting an "unused" volume.
- A practice VM needs its own VM ID, isolated state and inventory.
- Generic API/SSH prerequisites: [PRE_REQUIRE.md](./PRE_REQUIRE.md).
