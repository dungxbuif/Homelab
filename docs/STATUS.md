---
type: Dashboard
title: "Homelab Current Status"
description: "One-page current status and genuinely open gates"
timestamp: 2026-10-31T12:00:00+07:00
---

# Homelab Current Status — 2026-10-31

Based on the 2026-10-31 read-only live audit (Pi5, VM100, VM110) and the
[VPS gateway audit](./deployments/vps-gateway-audit-2026-10-31.md). Proxmox
and MikroTik were not audited live. Full catalog: [STACK.md](./STACK.md).
Open work list: [BACKLOG.md](./BACKLOG.md).

## Summary

| Area | State |
|---|---|
| Public edge | Up. VPS Traefik -> Rathole -> Pi5 Traefik; homepage 200, GitLab 302, NetBird relay 404 (expected) |
| Swarm | Pi5 leader + VM100 + VM110; `orangepizero3` down but still a member; five 0/0 leftover services |
| Apps | All production Swarm services 1/1; RelayHub v1 (Rust) is the public writer, legacy Go Compose on VM100 is rollback only |
| Data | Pi5 hosts PostgreSQL 16.15, PgBouncer, CouchDB 3.5.3, RustFS 1.0.4, Redis 7.2 — all upgraded and restore-checked 2026-10-31 |
| Backups | Databasus (VM110) backs up and restore-verifies 6 service DBs to Google Drive. **No scheduled backup timers on any host**; GitLab, RustFS, CouchDB, Redis and configs have no recurring backup |
| Monitoring | VictoriaMetrics + Alertmanager on Pi5; VM100 drift timer active |
| Capacity | Pi5 disk 42%, VM100 66%, VM110 65%, VPS 20% |
| Automation | Semaphore v2.19.17 on Pi5 for reviewed host tasks; most stacks still deployed by hand (see plan) |

## Open gates

| ID | Gate | Done when |
|---|---|---|
| S0 | MikroTik DHCP may hand out DNS `10.10.0.2` (dead Orange Pi) — **verify urgently** | Live DHCP DNS confirmed `10.10.0.5` |
| S1/S3 | Rotate previously exposed GitHub credentials and the GitLab PAT exposed 2026-10-31 | Issuer-side revocation evidence |
| S4 | VPS: UFW inactive, no container healthchecks, no external NetBird/RustDesk session test | Firewall on with approved ports, probes, session smoke |
| B0 | No recurring backup for GitLab, RustFS, CouchDB, Redis, host configs | One owner/schedule per class with an observed scheduled run |
| B3 | No VM image backup (no separate failure-domain target) | Off-host target plus verified `vzdump` restore |
| U0 | GitLab 18.11.11 not upgraded; native backup too large to complete | Feasible GitLab backup/restore, then staged upgrade (needs PostgreSQL 17) |
| C1 | Pi5 cloudflared flaps: `Unauthorized: Tunnel not found` (deferred) | Token repaired or connector retired |
| P1/P4 | Swarm leftovers, down Orange Pi node, legacy RelayHub Go rollback | Owner-confirmed removal |
| R13 | `db-management_mezon_webhook` secret does not match the intended webhook | Replaced via release path, delivery verified |

## Forward plan

[Lab-wide IaC automation rebuild](./superpowers/plans/2026-10-31-lab-iac-automation-rebuild.md)
(status: proposed) is the only roadmap.

## Operator rules

1. Read this page, STACK.md and BACKLOG.md before changing infrastructure.
2. Code changes go to `/home/dungxbuif/workspace/projects/homelab-ops`; this
   vault records current state, evidence and rollback notes.
3. Stateful changes need a fresh backup, a restore check and a recorded
   rollback. Never delete or recreate data volumes as a first response.
4. No secret values in this vault — names and locations only.
