---
type: Dashboard
title: "Homelab Current Status"
description: "Single-page current status, verified boundaries, and remaining gates for operators and agents"
timestamp: 2026-10-26T22:42:21+07:00
---

# Homelab Current Status

**Last reconciled:** 2026-10-26 22:42 (Asia/Ho_Chi_Minh)

**Latest runtime snapshot:** [Homelab Runtime Verification — 2026-10-26](./deployments/2026-10-26-homelab-runtime-verification.md)

The latest read-only check found db-management API, worker, web, CloudBeaver
and Databasus at `1/1`. db-management completed a real CouchDB
export/upload/verify operation to Google Drive. Databasus health and schedulers
are running, but authenticated provider configuration, a Databasus Drive backup,
remote retention deletion, and Databasus restore are not proven.

**Documentation check:** 170 active Markdown files under `docs/` were checked.
There are no missing operational relative links; the four remaining warnings
are illustrative URL examples in `OKF_SPEC.md`. Archived historical pages are
excluded from the current-runtime check.

This is the short operational index. It summarizes the latest evidence; it does
not replace dated deployment records or the [backlog](./BACKLOG.md). Historical
documents may describe an earlier state and are intentionally retained for
incident and rollback context.

## Current operating model

| Area | Current state | Evidence |
|---|---|---|
| Public edge | VPS HostSNI gateway -> Rathole -> Pi5 Traefik | [system playbook](./MAIN.md) |
| Compute | VM100 (`10.10.0.31`) runs user-facing workloads; VM110 (`10.10.0.32`) is the new backup/DB-operations worker | [VM100 reference](./VM100.md), [Proxmox reference](./PROXMOX.md) |
| Data | Pi5 (`10.10.0.5`) remains the authoritative PostgreSQL, Redis, CouchDB and RustFS host | [Pi5 specification](./PI.md) |
| Automation | Semaphore/Ansible handles reviewed host operations; VM100 systemd owns backup schedules | [automation runbook](./runbooks/automation-operations.md) |
| Backups | Google Drive is the single off-site target; database-instances, databases, GitLab, RustFS, configs and restore-drill classes are active | [backup runbook](./runbooks/backup-restore.md) |
| Kubernetes | No production Kubernetes cluster or VM exists; old K8s material is archived | [Proxmox reference](./PROXMOX.md) |

## Verified complete

- Restore acceptance passed for PostgreSQL/database-instances, GitLab, shared
  PostgreSQL/CouchDB payloads and RustFS. Monthly unattended restore drill is
  enabled.
- Host-config backup, health/dead-man checks, Pi5 backup resource caps, VM100
  disk maintenance and manager-side Swarm inventory are deployed.
- RustFS and PostgreSQL native-pull paths are verified. The experimental
  CouchDB stream exporter now has a per-page free-space guard and source
  contract coverage, but Pi5 remains the rollback path for the database class
  while the full CouchDB stream restore is being evaluated.
- Current VM100 resource limits, AI selector rollout, monitoring target
  cleanup and retired-service cleanup are documented in dated evidence records.

## Remaining gates

| ID | Gate | Current truth | Completion evidence |
|---|---|---|---|
| S1 | Rotate previously exposed GitHub credentials | Pattern audit is clean; issuer-side rotation is not evidenced | New issuer credentials plus revocation evidence |
| S2 | VPS HostSNI live validation | Guard contract passes locally; live VPS dry-run and route smoke are pending operator access | Approved hash, dry-run output and bounded public smoke |
| A1 | AI rollout owner UAT | Runtime and synthetic matrix pass; business acceptance is still separate | Owner-approved UAT record |
| A8 | GitLab CI Homepage release | Source contract and tests pass; protected variables, runner enrollment and live positive/no-op runs remain | GitLab pipeline receipts |
| B3 | VM100 image backup | Proxmox has no separate failure-domain target | PBS/NAS/other target and a verified `vzdump` restore |
| B9 | Passive Pi5 backups | RustFS/PostgreSQL are native-pull; CouchDB has a guarded stream uploader, durable metadata snapshot and manual two-snapshot restore orchestrator, but the full `homelab` comparison is still pending | Complete export, representative restore, scheduler cutover and rollback test |

## Operator rules

1. Read this page and `BACKLOG.md` before changing infrastructure.
2. Treat a dated deployment record as evidence for that change only; do not
   infer that an older “pending” sentence describes the current runtime.
3. Never move Pi5 data services or enable a new backup transport without a
   restore test and an explicit rollback path.
4. Keep secrets and issuer values out of this repository; record only references
   and verification evidence.
