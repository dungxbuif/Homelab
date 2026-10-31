---
type: Service
title: n8n
description: n8n workflow automation with external task runners, Swarm services on VM100 at n8n.dungxbuif.com
generated:
  by: claude-code/opus-5.5
  at: "2026-10-31T15:00:00+07:00"
stale_after: "2027-01-29T15:00:00+07:00"
lifecycle: active
class: internal
owner: dungxbuif
deployed_revision: 2.46.3
---

# n8n

## Summary

Workflow automation for the owner (Mezon bots, webhooks, private search via
SearXNG). Third-party app; no repo docs of ours. Class `internal` (unverified
intake), status `active`.

## Source

| Field | Value |
|---|---|
| Upstream | https://github.com/n8n-io/n8n |
| Pinned version | `ghcr.io/n8n-io/n8n:2.46.3@sha256:1a6e1865…`; runners `n8nio/runners:2.46.3@sha256:e10899bf…` (pair must match) |
| Custom nodes | [n8n-nodes-mezon](../projects/n8n-nodes-mezon.md) installed in `/opt/apps/n8n/data/nodes/` (plus `mezon-sdk`) |
| Deploy source | none: created with `docker service create`, no stack file in `homelab-ops` |

## Internal architecture

`n8n` runs workflows and the task broker; `n8n-runners` executes Code-node
tasks in external mode, authenticated by a shared runner token. n8n reaches
`knowledge-hub-search` (SearXNG Compose on VM100) over `knowledge-hub-net`.

## Runtime

| Field | Value |
|---|---|
| Host / placement | VM100 (`node.hostname==vm100-prod`) |
| Services | `n8n`, `n8n-runners` (no stack) |
| Domain / exposure | `n8n.dungxbuif.com` → `tasks.n8n:5678` via Pi5 Traefik (public/LAN split unverified) |
| Networks | n8n: `edge-http-net`, `data-net`, `knowledge-hub-net`; runners: `data-net`, `knowledge-hub-net` |
| Limits | n8n 1 CPU / 2 GiB; runners 0.5 CPU / 512 MiB; no reservations |
| Healthcheck | n8n `wget /healthz`; runners none |
| Update | `failure_action: rollback` |

## Data

| Store | Name | Backup class | Last restore evidence | RPO / RTO |
|---|---|---|---|---|
| PostgreSQL (Pi5, `pgbouncer:6432`) | `n8n` | Databasus → Google Drive | automatic restore verification passed 2026-10-31 ([record](../deployments/backup-repair-2026-10-31.md)) | not stated |
| Bind mount | `/opt/apps/n8n/data` (VM100) | none | none | not stated |

## Secrets

Passed as **plain env vars**, not Swarm secrets: `N8N_ENCRYPTION_KEY`,
`N8N_RUNNERS_AUTH_TOKEN`, `DB_POSTGRESDB_PASSWORD`. 1Password item paths
(unverified). Losing `N8N_ENCRYPTION_KEY` makes stored credentials unreadable.

## Delivery

- Manual `docker service update --image` from the Pi5; upgrade record
  [version-upgrade-2026-10-31](../deployments/version-upgrade-2026-10-31.md).
- Rollback: `docker service rollback n8n` and `n8n-runners` together.

## Operations

- Health: `https://n8n.dungxbuif.com/healthz`
- Logs: `docker service logs n8n` / `n8n-runners` (Pi5)
- Known issue: n8n and runners must run the same version, or Code nodes fail.

## Gate status

| Gate | State | Evidence / exception (expiry) |
|---|---|---|
| G0 Intake | fail | no `app.yml` |
| G1 Build | partial | upstream image pinned by digest; no scan |
| G2 Security | fail | secrets in env vars |
| G3 Runtime | fail | `docker service create`, no stack; runners lack healthcheck |
| G4 Data | partial | DB restore verified; data dir not backed up; no RPO/RTO |
| G5 Observability | not assessed | |
| G6 Release | not assessed | |
| G7 Docs | partial | this doc |
| G8 Operate | not assessed | |

## Recent changes

- 2026-10-31: upgraded n8n and runners to `2.46.3` (pair matched).
- 2026-10-31: `n8n` DB enrolled in Databasus restore verification.
