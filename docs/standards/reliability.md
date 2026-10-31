---
type: Standard
title: "Reliability Contract"
description: "What a green pipeline guarantees, how changes are fenced before prod, the single points of failure and the measured reliability targets"
status: draft
generated:
  by: claude-code/opus-5.5
  at: 2026-10-31T19:30:00+07:00
stale_after: 2027-01-29T19:30:00+07:00
tags: [reliability, slo, ci, rollback]
---

# Reliability Contract

A green pipeline means the system is verified to be working, not merely that a deploy command finished.

## 1. Green only after verification

| Step | Check | On failure |
|---|---|---|
| Converge | Swarm reports the desired replicas with the **expected digest**, and no task is restart-looping | Auto-rollback, red |
| Health | Every container healthcheck is healthy | Auto-rollback |
| Functional smoke | A per-app script exercises real API calls (login, read, write probe) over **both the LAN path and the public path** | Auto-rollback |
| Bake (10 min) | Error rate and latency stay within thresholds (VictoriaMetrics + blackbox). Memory stays under 90% of the limit | Auto-rollback |
| Data | A fresh backup exists before any migration, and the migration finished | Stop, no promotion |
| Drift | A post-deploy drift check finds that live matches the repo | Red |
| Receipt | Digest, time, smoke and metrics are written to the vault (doc-bot) and to Mezon | — |

Infrastructure changes (tofu, ansible) follow the same contract: apply → probe the affected routes and services → roll back to the previous state or config on failure.

## 2. Fences before prod

- **One change at a time:** GitLab `resource_group` serialises deploys and applies.
- **Host canary order:** VM110 → VM100 → VPS → **Pi5 last**. Each step must pass its probe.
- **Staging first:** prod only receives the digest that passed staging.
- **Preflight:** disk and RAM headroom, fresh backups and no open critical alert. Otherwise apply is refused.
- **Saved plans only:** tofu applies exactly the plan file commented on the MR.
- **Incident lock:** while a critical alert is open, only rollback jobs may run.

## 3. Single points of failure and mitigation

| SPOF | Mitigation | Phase |
|---|---|---|
| Pi5 as the only Swarm manager | Three managers: Pi5, VM100, VM110 | P2 |
| Pi5 datastores on one SSD | Verified backups + monthly drills. Optional PostgreSQL hot standby on VM110 | P6 |
| Edge only on Pi5 | Edge fully in code, rebuilt on VM100 by playbook in ~15 min, drilled | P3 |
| One Proxmox host and `local-lvm` | Off-host VM images, tofu + ansible rebuild, quarterly drill | P6 |
| One VPS | `gateway_vps` role rebuilds a new VPS in ~30 min. Dead-man alert | P3 |
| GitLab (CI, registry, source) | Verified backups, GitHub push mirrors, break-glass from the workstation | P0 |
| Power and ISP | UPS for Proxmox, Pi5 and the router (to confirm). The ISP risk is accepted | — |

## 4. Targets (measured, reported weekly to Mezon)

| Metric | Target |
|---|---|
| Availability of `public` apps (external probe through the VPS) | ≥ 99.5% per month |
| Change failure rate | < 10% |
| Recovery from a bad deploy | < 5 min (auto-rollback) |
| Data RPO / RTO | 24 h / 4 h. GitLab 24 h / 2 h |
| Manual drift | 0 |
| Restore drills | 100% pass each month |

An app that has exhausted its monthly error budget may only receive fixes until the next month.
