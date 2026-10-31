---
type: Service
title: KubeKosh
description: KubeKosh privileged K3s training lab, manual Compose on VM100, LAN-only at kubekosh.dungxbuif.com
generated:
  by: claude-code/opus-5.5
  at: "2026-10-31T15:00:00+07:00"
stale_after: "2027-01-29T15:00:00+07:00"
lifecycle: lab
class: lab
owner: dungxbuif
deployed_revision: "zeborg/kubekosh:latest (unpinned)"
---

# KubeKosh

## Summary

Kubernetes training sandbox (K3s inside a privileged container). Not a
managed cluster and not part of the lab platform. Third-party app; class
`lab`, status `lab`. Keep or retire is an open question in the IaC plan.

## Source

| Field | Value |
|---|---|
| Upstream | Docker Hub `zeborg/kubekosh` (source repo unverified) |
| Pinned version | **`zeborg/kubekosh:latest`** — not pinned |
| Deploy source | manual Compose `/opt/apps/kubekosh/docker-compose.yml` on VM100 |

## Runtime

| Field | Value |
|---|---|
| Host | VM100, Compose project `kubekosh`, container `kubekosh` |
| Domain / exposure | `kubekosh.dungxbuif.com`, LAN-only via Pi5 `lan-only` middleware |
| Limits | 2 CPU / 4 GiB |
| Privileged | yes (needed for K3s) |

## Data

| Store | Name | Backup class | Last restore evidence | RPO / RTO |
|---|---|---|---|---|
| Bind | `/opt/apps/kubekosh/data` | none | n/a | data may be lost (lab) |

## Secrets

None recorded.

## Delivery

- Manual `docker compose pull && up -d` on VM100. Rollback: none (`latest`).

## Operations

- Logs: `docker logs kubekosh` on VM100.

## Gate status

| Gate | State | Evidence / exception (expiry) |
|---|---|---|
| G0 Intake | fail | no `app.yml` |
| G1 Build | fail | `latest` tag, no digest |
| G2 Security | fail | privileged container on the production VM |
| G3 Runtime | fail | manual Compose; plan P5 keeps it via `compose_app` or retires it |
| G4 Data | pass | lab class: data may be lost (declared here) |
| G5 Observability | not assessed | |
| G6 Release | n/a | not required for `lab` |
| G7 Docs | partial | this doc |
| G8 Operate | not assessed | |
