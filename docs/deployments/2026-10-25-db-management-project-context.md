---
type: Deployment
title: "DB-management project and Homelab context"
description: "Canonical map of the DB-management application, operations repository, runtime placement, backup boundary, and acceptance status"
timestamp: 2026-10-25T00:00:00+07:00
---

# DB-management project context

This page is the short cross-repository map for the new `db-management`
project. It records ownership and observed boundaries; it is not a claim that
every database workflow or restore has passed.

## Repository ownership

| Area | Repository / path | Owns |
| --- | --- | --- |
| Application | `/home/dungxbuif/workspace/db-management/` | NestJS/Bun API, worker, adapter contracts, web UI, tests and GitLab pipeline |
| Operations | `/home/dungxbuif/workspace/homelab-ops-task1/` | Swarm stack, VM110 bootstrap, Pi5 release boundary, secrets/config references and ops verification |
| Homelab record | `/home/dungxbuif/workspace/vaults/homelab/` | Topology, deployment evidence, runtime inventory, decisions and rollback notes |

Remotes:

- App: `ssh://git@gitlab.dungxbuif.com:2222/dungxbuif/db-management.git`
- Ops: `ssh://git@gitlab.dungxbuif.com:2222/dungxbuif/homelab-ops.git`
- Homelab vault: `git@github.com:dungxbuif/Homelab.git`

The app repository owns application behavior. The ops repository owns the
deployment implementation. This vault must not become a second CI, Ansible or
service implementation.

## Homelab placement and traffic

```text
Pi5 10.10.0.5
  active LAN DNS / Traefik edge, Swarm manager, PostgreSQL/PgBouncer,
  Redis-prod, CouchDB, and the restricted db-management release boundary

VM110 10.10.0.32
  Swarm worker for db-management API/worker/web, CloudBeaver and Databasus

Pi5-routed private HTTPS
  db-management.dungxbuif.com  -> db-management web/API
  cloudbeaver.dungxbuif.com   -> CloudBeaver
  databasus.dungxbuif.com     -> Databasus
```

The application is intentionally LAN/NetBird scoped and has no application
authentication flow. CloudBeaver remains the PostgreSQL tool boundary and
Databasus remains a separate provider/UI boundary; their health endpoints do
not prove an authenticated workspace, provider, backup or restore.

## Backup ownership

The db-management worker owns database payload backup for PostgreSQL and
CouchDB/Couchloom sources. It uses database adapters plus the Google Drive SDK:

1. adapter exports a bounded, manifest-driven artifact set;
2. the worker requires `COMPLETE`, `manifest.json`, exact inventory and
   `checksums.sha256` before upload;
3. the Drive adapter uploads to `Homelab Backup/databases/<source>/<run>` and
   verifies file size and Drive MD5;
4. only after remote verification does it write `remote.json` and delete
   completed local staging;
5. successful remote runs are retained for seven days; failed/stale evidence
   is preserved.

Restic/rclone and the legacy scheduler are not runtime dependencies of the new
worker. Their old scripts, Semaphore resources and repositories are retained
until consumers are inventoried and retirement is explicitly approved.

Redis is currently monitor-only and is not included in db-management backup
ownership. Config, GitLab, RustFS and other non-database payloads remain outside
this worker boundary.

## Current evidence — 2026-10-25

- Live Swarm services observed `1/1`: API, worker, web, CloudBeaver and
  Databasus.
- Pi5-routed HTTPS checks returned `200` for API readiness, CloudBeaver status
  and Databasus health.
- Fresh native Drive jobs succeeded for PostgreSQL, CouchDB Obsidian, Couchloom
  PostgreSQL and CouchDB Homelab. Each had completion marker, manifest,
  checksums, payload and remote Drive evidence; completed local staging was
  absent after upload.
- GitLab pipeline [#501](https://gitlab.dungxbuif.com/dungxbuif/db-management/-/pipelines/501)
  passed quality, ops-contract, image build, digest scan and release-manifest.
  Its deploy job remained manual and was not run.

Detailed evidence and exact job identifiers are in the
[DB-management core audit](./2026-10-25-db-management-core-audit.md).

## Acceptance status

The project is operational for the observed backup path, but not fully
accepted as production-ready. The remaining gates are:

1. enroll the dedicated Pi5 release identity and add protected GitLab key and
   pinned `known_hosts` file variables;
2. run and verify one protected release plus its receipt/observed image
   digests, then verify rollback;
3. perform isolated PostgreSQL and CouchDB restore exercises;
4. if Databasus is kept, configure and verify its authenticated workspace,
   provider/storage, retention and isolated restore;
5. inventory and separately approve retirement of old Restic/rclone scripts
   and Semaphore resources.

Until those gates are evidenced, `live_verified` stays false in the ops lock
file and this page must not be read as a blanket production-ready statement.

## Source-of-truth links

- App docs: `db-management/docs/README.md`, `ci-cd.md`, `adapters.md`,
  `recovery-verification.md`
- Ops docs: `homelab-ops/automation/stacks/db-management/README.md` and
  `versions.lock.json`
- Current evidence: this vault's dated core audit and runtime inventory
- Recovery boundary: app `docs/recovery-verification.md`; actual restore is a
  separately authorized isolated operation, not an API endpoint

