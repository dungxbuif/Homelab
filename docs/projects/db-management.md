---
type: Project
title: db-management
description: LAN-only database administration and backup verification hub (API, worker, web, CloudBeaver, Databasus); Swarm stack on VM110
generated:
  by: claude-code/opus-5.5
  at: "2026-10-31T16:00:00+07:00"
stale_after: "2027-01-29T16:00:00+07:00"
lifecycle: active
project: db-management
class: internal
owner: dungxbuif
repo: dungxbuif/db-management
deployed_revision: unverified (live image digests match neither homelab-ops stack.yml nor versions.lock.json)
---

# db-management

## Summary

db-management is the internal database operations hub: catalog of PostgreSQL,
CouchDB and Redis sources, links into CloudBeaver, basic CouchDB admin,
Redis `redis-prod` monitoring, native backups to Google Drive from its worker,
and a record of backup/verification state from Databasus. It runs as the only
workload on VM110 `db-ops`, reachable on LAN/NetBird only. Class `internal`,
owner dungxbuif, status `active`. App-level authentication is deferred while it
stays LAN-only.

## Source

| Field | Value |
|---|---|
| Local checkout | `/home/dungxbuif/workspace/projects/db-management/` (on `main`, HEAD `535c81d`, 2026-10-25) |
| GitLab | `dungxbuif/db-management` (default branch `main`) |
| Repo docs | `README.md`, `docs/` (`adapters.md`, `ci-cd.md`, `compatibility.md`, `recovery-verification.md`, `runbooks/`) |
| Ops source | `homelab-ops/automation/stacks/db-management/` (`stack.yml`, `versions.lock.json`, `README.md`, `bootstrap-v*.json`) |
| Deployed revision | (unverified). Lock last records release `0.1.6-db-management-20261026`, app commit `41314f6`, ops commit `20d1f69` (2026-10-26); live digests have changed since |

## Internal architecture

- Bun workspace: NestJS `api` (port 3000) and `worker`, React/Vite `web` (nginx),
  shared `packages/{contracts,storage,adapters}`. SQLite catalog and job state
  on volume `db-management-state`.
- Worker runs native PostgreSQL/CouchDB/CouchLoom backups, stages under
  `/var/lib/db-management/backups/<job>-<token>/`, uploads to Drive
  `Homelab Backup/databases/<source>/<run>/`, retention 7 days, lease 1 h.
- Reaches data on VM100/Pi5 through the VM100 relay project
  `homelab-backup-db-ops-relay` (`10.10.0.31:15432` Pi5 PostgreSQL, `:15433`
  CouchLoom PostgreSQL, `:15984` CouchDB backup proxy).
- Third-party tools in the same stack: CloudBeaver (SQL UI) and Databasus
  (scheduled PostgreSQL backups to Drive with Pi5 `pi-verifier-1` restore
  agent). See [Databasus](../services/databasus.md).
- Redis is monitor-only and excluded from backup.

## Runtime

| Field | Value |
|---|---|
| Host / placement | VM110 `db-ops` (`node.hostname == db-ops`) for all services |
| Stack / services | Swarm stack `db-management` → `db-management_db-management-api`, `_db-management-worker`, `_db-management-web`, `_cloudbeaver`, `_databasus` |
| Image | `registry-gitlab.dungxbuif.com/dungxbuif/db-management/{api@sha256:d4fc982c…, worker@sha256:cf9bb789…, web@sha256:5fba26cf…}`; `dbeaver/cloudbeaver:26.2.3@sha256:0c875296…`; `databasus/databasus:v3.64.0@sha256:dca80ac1…` |
| Domain / exposure | `db-management.dungxbuif.com` → web, `cloudbeaver.dungxbuif.com`, `databasus.dungxbuif.com`; Pi5 file-provider routes with `lan-only` middleware; LAN/NetBird only |
| Networks | api: `db-management-net`, `homelab-control-net`, `homelab-net`; worker: `db-management-net`, `homelab-net`, `pg-net`; web: `db-management-edge-net`, `db-management-net`, `homelab-control-net`; CloudBeaver/Databasus: `db-management-edge-net`, `db-management-net`, `homelab-control-net`, `pg-net` |
| Limits | None set on any service (live inspect 2026-10-31) |
| Healthchecks | api `/health`, web `/`, CloudBeaver TCP 8978, Databasus `main healthcheck`; worker none |
| Update config | CloudBeaver `failure_action: rollback`; others `pause` |
| Volumes | `db-management-state`, `db-management-backups`, `db-management-cloudbeaver-workspace-v3`, `db-management-databasus-data` |

## Data

| Store | Name | Backup class | Last restore evidence | RPO / RTO |
|---|---|---|---|---|
| SQLite (app catalog/jobs) | volume `db-management-state` | none; recovery export `bun run recovery:export` | none | not stated |
| Databasus state | volume `db-management-databasus-data` | none | none | not stated |
| CloudBeaver workspace | `db-management-cloudbeaver-workspace-v3` | manual archive `/opt/apps/homelab-backup/runs/version-upgrade-20261031/cloudbeaver/workspace-v3.tgz` | archive listed 2026-10-31 | n/a |

Backups it produces for other apps are recorded in
[Databasus audit](../deployments/databasus-audit-2026-10-31.md) and the
[backup runbook](../runbooks/backup-restore.md).

## Secrets

| Secret (Swarm) | 1Password item | Used for |
|---|---|---|
| `db-management-backup-credentials-v2` | (unverified) | PostgreSQL/CouchDB/CouchLoom source credentials (api, worker) |
| `db-management-drive-credentials-v2` | (unverified) | Google Drive upload (worker) |
| `db-management-provider-credentials` | (unverified) | provider secrets (api, worker) |
| `db-management-redis-password` | (unverified) | `redis-prod` monitor (api, worker) |
| `db-management-session-secret` | (unverified) | API sessions |
| `db-management-mezon-webhook` | `Homelab Secret/Mezon - Homelab channel webhook` (intended; live value does not match, BACKLOG R13) | backup notifications |

## Delivery

- CI: `.gitlab-ci.yml` stages `quality` (bun test/typecheck/build) →
  `ops-contract` (validates `OPS_REF` of homelab-ops) → `build-images` (push to
  GitLab Registry) → `container-scan` (Trivy, blocks HIGH/CRITICAL) →
  `release-manifest` → `deploy-vm110` (manual, protected, Ansible). See repo `docs/ci-cd.md`.
- Staging: none. Prod: manual `deploy-vm110` job with `DB_MANAGEMENT_DEPLOY_APPROVED=true`.
- Rollback: redeploy the previous image tag via the same job; controlled
  rollback drill not executed (lock `verification_blocked_by`).
- Drift: live api/worker/web digests differ from `stack.yml` and the lock; reconcile before the next deploy.

## Operations

- Health: `https://db-management.dungxbuif.com/` (LAN), API `/health`, `https://cloudbeaver.dungxbuif.com/status`, Databasus health.
- Logs: `docker service logs db-management_db-management-worker` (from Pi5).
- Known issues: CloudBeaver 26.2.3 has no `curl` (TCP healthcheck used);
  Databasus Drive OAuth 401 / stale admin credential (BACKLOG R4); Proxmox
  `local-lvm` ~96% used affects VM110.

## Gate status

| Gate | State | Evidence / exception (expiry) |
|---|---|---|
| G0 Intake | partial | Stack dir exists in homelab-ops; no `app.yml` |
| G1 Build | partial | GitLab CI, registry, digest refs, Trivy gate; non-root/multi-stage not assessed |
| G2 Security | partial | Swarm secrets, no host ports; admin UIs rely on `lan-only` (app auth deferred); Mezon secret mismatch |
| G3 Runtime | fail | No resource limits; worker has no healthcheck; most services `failure_action: pause` |
| G4 Data | fail | Own state volumes not backed up; no restore record |
| G5 Observability | not assessed | |
| G6 Release | fail | Rollback drill not executed |
| G7 Docs | partial | Repo README/docs present; deployed revision unverified |
| G8 Operate | fail | Live digests drift from ops lock |

## Recent changes

- 2026-10-31: Databasus restore verification passed for 6 service DBs via `pi-verifier-1`
- 2026-10-31: CloudBeaver `25.3.5` → `26.2.3` after an automatic rollback and healthcheck fix (`80e56ed`)
- 2026-10-26: runtime recovered after VM110 storage incident; release `0.1.6-db-management-20261026` observed 1/1
