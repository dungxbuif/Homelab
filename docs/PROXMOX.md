# Proxmox Production Hypervisor

Proxmox at `10.10.0.20` hosts **production VM100**. The earlier AWS-only
description is superseded; do not treat the whole hypervisor or VM100 as
ephemeral. Current VM100 service/storage details are in [VM100.md](./VM100.md).

## Placement and Storage

| Field | Current documented state |
|---|---|
| Production VM | `100`, `vm100-prod`, LAN `10.10.0.31` |
| VM100 allocation | 6 vCPU, 16 GB RAM, 200 GiB disk per deployment record |
| Guest filesystem | ext4 root ~194 GiB; 65 GiB used, 130 GiB free in the 2026-09-16 SSH sample |
| Guest persistent state | GitLab config/data/repositories/Registry trial, app bind mounts and runtime volumes |
| Database placement | Pi5; never infer GitLab DB is on Proxmox from its application placement |
| Retired VMs | `101/102` removed per migration record; no hypervisor-side confirmation in this audit |
| Historical design | HA K8s, kube-vip, Longhorn and old workload topology; no such cluster or VM is active |

Guest disk increased from 80 to 200 GiB on 2026-09-15. After restart,
`discard=on` and guest `fstrim` returned thin-pool capacity in the recorded
audit. These are dated observations; logical guest free space is not proof
of current physical thin-pool headroom. Inspect `qm config 100`, storage
status and `lvs` before another resize or allocation cleanup.

## Operations and Recovery

- Protect VM100 from generic lab teardown and old Terraform state. Historical
  K8s state can still reference VM IDs now reused for production and must never
  be loaded by the active automation inventory.
- Back up IaC state before reconciliation; do not run a generic
  `terraform destroy` against the historical workspace.
- GitLab data lives on VM100 but its PostgreSQL DB is on Pi5. A VM snapshot
  alone does not constitute a complete application backup; use the
  [GitLab runbook](./services/gitlab.md) and verify restore consistency.
- Stop stateful workloads before destructive storage changes. Do not delete
  an allocated volume simply because it appears unused; reconcile VM/CT
  disks, snapshots and mounts first.
- [PRE_REQUIRE.md](./PRE_REQUIRE.md) covers generic API/SSH prerequisites;
  it does not authorize recreating the retired cluster.

## Active OpenTofu Boundary

The active module is
[`automation/tofu/proxmox/`](../automation/tofu/proxmox/). It models only the
existing VM ID `100` and uses an explicit import block. The module has
`prevent_destroy = true`; it does not contain VM IDs `101`/`102`, Kubernetes
nodes, kube-vip, or a cluster target. The first Semaphore plan must be
import-only or a reviewed zero-destroy delta before any sizing change.

The current import backend is a private local state path on the controlled
runner. A RustFS state backend is a later change and requires bucket
versioning, credentials, locking, and restore verification first. Proxmox API
tokens are supplied by Semaphore variables and never stored in Git.

## Optional Practice Lab

No Kubernetes or other practice VM is part of the current lab inventory. A
future practice VM requires an explicit request, a dedicated VM ID, isolated
OpenTofu state, and a separate automation inventory; it must not share VM100's
production lifecycle.

## Historical Context

The former AWS-only guide is preserved in
[the archive](./archived/superseded-topology/proxmox-aws-only-before-20260916.md).
The original K8s design remains in [k8s-v2](./archived/k8s-v2/PROXMOX.k8s.md).
