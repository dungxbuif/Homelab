---
type: Reference
title: "DB-management project and Homelab reference"
description: "The source-of-truth map for the adapter-based database operations app and its private Homelab runtime"
timestamp: 2026-10-26T07:56:00+07:00
---

# DB-management project and Homelab reference

This is the short operational map for the new `db-management` project. It
connects application code, deployment code, live placement and acceptance
evidence without copying the implementation into the Homelab vault.

## Ownership and repositories

| Repository | Local checkout | Owns |
| --- | --- | --- |
| `db-management` | `/home/dungxbuif/workspace/projects/db-management/` | NestJS/Bun API, worker, shadcn web UI, adapter contracts, Drive upload and GitLab CI |
| `homelab-ops` | `/home/dungxbuif/workspace/homelab-ops-task1/` | Swarm stack, VM placement, external secrets/config references, release boundary and ops contract tests |
| `homelab` | `/home/dungxbuif/workspace/vaults/homelab/` | topology, decisions, live evidence, runbooks and acceptance gates |

Remotes:

- App: `ssh://git@gitlab.dungxbuif.com:2222/dungxbuif/db-management.git`
- Ops: `ssh://git@gitlab.dungxbuif.com:2222/dungxbuif/homelab-ops.git`

The vault is documentation only. Do not add a second worker, scheduler,
adapter implementation or deployment path here.

## Intended product boundary

`db-management` is a private-LAN database operations catalog and backup worker.
It is intentionally not a replacement for every database vendor's admin UI.

| Capability | Current design |
| --- | --- |
| PostgreSQL | Adapter-owned export and verified Drive artifact upload |
| CouchDB/Couchloom | Adapter-owned export, manifest/checksum verification and Drive upload |
| Redis | Read-only monitoring (`redis-prod-monitor`); no backup ownership |
| CloudBeaver | Bookmark/admin UI for interactive PostgreSQL work; its credentials remain in CloudBeaver |
| Databasus | Separate backup UI/provider boundary; health is monitored, but authenticated provider/restore acceptance remains open |
| Future databases | Add an adapter/factory implementation and acceptance tests; do not add vendor logic to the UI layer |

The worker's successful backup contract is: complete export, manifest,
checksums, Drive upload, remote metadata verification, local receipt, then
cleanup of verified staging. Failed or incomplete staging remains evidence for
investigation. Retention is seven days for successful Drive runs; Redis and
configuration files are outside this worker's backup ownership.

## Runtime topology

```text
LAN / private DNS
       |
       v
Pi5 10.10.0.5
  Swarm manager + Traefik/AdGuard edge
  PostgreSQL/PgBouncer, Redis-prod, CouchDB, RustFS and release boundary
       |
       | encrypted/private Swarm overlay and LAN routes
       v
VM110 10.10.0.32 (db-ops)
  db-management API + worker + web
  CloudBeaver + Databasus

VM100 10.10.0.31 (vm100-prod)
  GitLab CE and other production workloads
  PostgreSQL/CouchDB relay services used by selected source connections

Proxmox 10.10.0.20
  VM100 and VM110 hypervisor
```

Private routes:

- `https://db-management.dungxbuif.com/`
- `https://cloudbeaver.dungxbuif.com/`
- `https://databasus.dungxbuif.com/`

The app has no user-authentication flow by design. Network restriction is the
access boundary; CloudBeaver and Databasus retain their own authentication.
Never treat a healthy HTTP endpoint as proof of an authenticated provider or a
successful backup.

## Components and responsibilities

| Component | Runs on | Responsibility | Proof endpoint/check |
| --- | --- | --- | --- |
| API | VM110 | catalog, backup requests, readiness and job status | `/health/ready` |
| Worker | VM110 | adapter execution, Drive verification, retention and optional Mezon notification | worker heartbeat in readiness and job records |
| Web | VM110 | operator UI built with shadcn variants; monochrome/white primary visual system | private web route |
| CloudBeaver | VM110 | interactive database administration | `/status` plus GraphQL schema/private-session probe |
| Databasus | VM110 | separate backup UI and provider workflow | `/api/v1/system/health` plus authenticated provider acceptance |
| Release boundary | Pi5 | accepts only bounded, verified app image manifests | protected forced-command receipt |
| GitLab | VM100 | source, registry, CI and audit trail | HTTPS API, SSH `:2222`, pipeline evidence |

## Release path

1. Local gates: `bun install --frozen-lockfile`, `bun test`, `bun run
   typecheck`, `bun run build`.
2. GitLab `quality` and `ops-contract` validate the app and the pinned
   `homelab-ops` SHA.
3. Image build and digest-pinned scan produce API, worker and web image
   digests.
4. The release manifest carries only bounded SHAs, digests and verification
   results.
5. A protected manual job sends the manifest to the Pi5 release identity.
6. The forced command updates only the three mutable app services and waits
   for API/worker readiness. CloudBeaver, Databasus, secrets, networks and
   volumes are outside that normal image-release boundary.

The last recorded app release was pipeline `537`, with validation pipeline
`569` for the later contract/documentation changes. GitLab is currently not a
closed gate: after the VM recovery, `gitlab_gitlab` is still reported `0/1`
and the HTTPS API returns `502`. Do not push or claim a new CI result until
GitLab returns a successful API response and the pipeline is observed.

## Current verified state — 2026-10-26 07:56 ICT

- Swarm nodes `db-ops` and `vm100-prod` are `Ready`; the Orange Pi node is
  still down and is not part of this app's placement.
- API readiness: HTTP `200`.
- Redis monitor status and metrics: HTTP `200`; this confirms observation only,
  not Redis backup.
- Backup-job inventory: 20 succeeded, 5 failed historical records, 3 queued
  and 1 running at the time of the check. Historical failures are retained;
  this is not a claim that every current scheduled job has completed.
- CloudBeaver status: HTTP `200`; its expired server configuration was repaired,
  anonymous access is disabled, and the private PostgreSQL smoke succeeded
  without saving credentials.
- Databasus health: HTTP `200`; authenticated workspace/provider, retention,
  backup and restore acceptance are still open.
- Proxmox VM100 and VM110: `running`, QEMU `qmpstatus=running` after recovery.
  The incident was caused by a full `local-lvm` thin pool and was recovered by
  extending the thin pool with existing free VG space and restarting the VMs.
  No VM disk or rollback snapshot was deleted.
- Proxmox `local-lvm`: approximately 13.7 GiB free and 96% used after
  recovery. This is an operational warning, not a capacity-ready state; thin
  allocation is still overcommitted and automatic thin-pool growth has not
  been proven.

## Open gates

1. Restore GitLab service health, push the pending `homelab-ops` security/docs
   commits and observe a successful protected pipeline.
2. Configure and authenticate Databasus through its supported UI/CLI, then
   record provider, retention, backup and isolated restore evidence.
3. Exercise the bounded app rollback during an approved maintenance window.
4. Inventory Semaphore, relay and CouchDB-proxy consumers before retiring any
   legacy script or service.
5. Add a Proxmox storage capacity/autoextend control before calling the
   production base fully reliable.

## Safe operator rules

- Do not delete the VM100 rollback snapshot or old backup evidence to solve
  capacity without an explicit storage decision.
- Do not reset Databasus data to solve a login problem.
- Do not place database credentials, GitLab tokens or SSH keys in these docs.
- Do not use `/status`, a running container or a `1/1` replica count as a
  substitute for the component-specific acceptance probe.
- Keep backup and restore actions separate: the API has no production restore
  endpoint, and restore drills target disposable isolated databases only.
