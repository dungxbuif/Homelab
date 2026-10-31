---
type: Service
title: CloudBeaver
description: CloudBeaver web DB client in the db-management stack on VM110, LAN-only at cloudbeaver.dungxbuif.com
generated:
  by: claude-code/opus-5.5
  at: "2026-10-31T15:00:00+07:00"
stale_after: "2027-01-29T15:00:00+07:00"
lifecycle: active
class: internal
owner: dungxbuif
deployed_revision: 26.2.3
---

# CloudBeaver

## Summary

Browser-based database client for the Pi5 PostgreSQL. Runs as part of the
`db-management` stack (see [db-management](../projects/db-management.md)).
Third-party app; class `internal`, status `active`.

## Source

| Field | Value |
|---|---|
| Upstream | https://github.com/dbeaver/cloudbeaver |
| Pinned version | `dbeaver/cloudbeaver:26.2.3@sha256:0c875296…` |
| Deploy source | `homelab-ops/automation/stacks/db-management/stack.yml` (stack label still pins `25.3.5` → running image updated by hand; file drift) |

## Internal architecture

Single service with a workspace volume holding users, saved connections and
settings. Reaches databases over `pg-net`.

## Runtime

| Field | Value |
|---|---|
| Host / placement | VM110 (`node.hostname == db-ops`) |
| Service | `db-management_cloudbeaver` |
| Domain / exposure | `cloudbeaver.dungxbuif.com`, LAN via Pi5 edge |
| Networks | `db-management-edge-net`, `db-management-net`, `homelab-control-net`, `pg-net` |
| Limits | **none set** |
| Healthcheck | TCP connect to `:8978` |
| Update | `failure_action: rollback` |

## Data

| Store | Name | Backup class | Last restore evidence | RPO / RTO |
|---|---|---|---|---|
| Volume | `db-management-cloudbeaver-workspace-v3` | none | none | not stated |

## Secrets

No Swarm secrets. Admin credentials and saved DB connections live in the
workspace volume. 1Password item (unverified).

## Delivery

- Manual image update; the 2026-10-31 upgrade needed an automatic rollback and
  retry ([record](../deployments/version-upgrade-2026-10-31.md)).
- Rollback: `docker service rollback db-management_cloudbeaver`.

## Operations

- Health: `https://cloudbeaver.dungxbuif.com/` (LAN)
- Logs: `docker service logs db-management_cloudbeaver` (Pi5)
- Known issue: Docker Hub rate limit (HTTP 429) on pulls; retry later.

## Gate status

| Gate | State | Evidence / exception (expiry) |
|---|---|---|
| G0 Intake | not assessed | part of db-management stack |
| G1 Build | partial | upstream image pinned by digest |
| G2 Security | not assessed | admin UI behind CloudBeaver login, LAN only |
| G3 Runtime | partial | in a stack, but no limits and file drift |
| G4 Data | fail | workspace volume not backed up |
| G5 Observability | not assessed | |
| G6 Release | not assessed | |
| G7 Docs | partial | this doc |
| G8 Operate | not assessed | |

## Recent changes

- 2026-10-31: upgraded to `26.2.3` after one automatic rollback.
