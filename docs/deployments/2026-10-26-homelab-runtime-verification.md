---
type: DeploymentEvidence
title: "Homelab Runtime Verification"
description: "Current topology, repository ownership, db-management evidence, and open acceptance gates"
timestamp: 2026-10-26T22:42:21+07:00
---

# Homelab Runtime Verification — 2026-10-26

This is the latest consolidated snapshot for operators and agents. It records
facts checked against the live lab or existing evidence. Older dated notes stay
as history and rollback context.

## Repository ownership

| Surface | Location | Ownership |
|---|---|---|
| Homelab record | `/home/dungxbuif/workspace/vaults/homelab` | topology, runtime evidence, decisions and runbooks |
| Ops repository | `/home/dungxbuif/workspace/homelab-ops` | canonical GitLab repository for deployment/automation code; migration merged to `main` at `a079e84`, README boundary at `01a8570` |
| Migration worktree | `/home/dungxbuif/workspace/homelab-ops-task1` | branch `codex/task1-migration-inventory`, retained for migration history and evidence |
| Application | `/home/dungxbuif/workspace/db-management` | NestJS/Bun application, adapters, UI and app CI |

The copied operational code is now present in `homelab-ops/main`. The vault
source was intentionally retained until old Semaphore/systemd consumers are
formally retired. Do not create a second implementation under this vault.

## Topology

| Node | Address | Current role |
|---|---:|---|
| VPS gateway | `103.82.21.202` | public edge and tunnel endpoint |
| Proxmox | `10.10.0.20` | hypervisor for VM100 and VM110 |
| Pi5 | `10.10.0.5` | Swarm manager, LAN edge/DNS, PostgreSQL, Redis, CouchDB and RustFS |
| VM100 | `10.10.0.31` | production compute and GitLab filesystem |
| VM110 (`db-ops`) | `10.10.0.32` | db-management and backup/restore worker |
| Orange Pi | `10.10.0.2` | retired/unavailable edge |

Normal public traffic is `VPS -> Rathole -> Pi5 Traefik`. Private names should
resolve through Pi5 AdGuard to `10.10.0.5`; the current workstation can still
select the public VPN DNS route.

## db-management runtime

The following Swarm services were `1/1`:

| Service | Route | Result |
|---|---|---|
| API | `https://db-management.dungxbuif.com` | readiness and worker heartbeat `ok` |
| Worker | internal | adapter/export/upload/verify execution |
| Web | `https://db-management.dungxbuif.com` | operator UI |
| CloudBeaver | `https://cloudbeaver.dungxbuif.com` | LAN HTTP 200 |
| Databasus | `https://databasus.dungxbuif.com` | health HTTP 200 |

Current app release: `v0.2.2-db-management-20261026`; GitLab pipeline 590 and
deploy job 1832 succeeded.

## Database ownership

- PostgreSQL is a bookmark/tool boundary. CloudBeaver owns direct PostgreSQL
  administration; db-management does not duplicate native PostgreSQL features.
- CouchDB is managed by the db-management adapter/SDK boundary. The live source
  catalog exposed eight CouchDB/bookmark/monitoring sources.
- Redis is monitor-only in db-management and is not owned by its backup flow.
- Databasus is a separate UI/provider service. Its db-management adapter remains
  unsupported until an authenticated, versioned workflow is proven.

## Verified db-management backup

One real CouchDB operation completed export -> staging -> Google Drive SDK upload
-> verification:

| Item | Evidence |
|---|---|
| Source | `couchdb-prod:obsidian_vault` |
| Operation | `4738b630-ad5b-4cdf-9cc3-353a751991f9` |
| Storage reference | `gdrive://1Qor8zp5RiXYkzgVw3wHXQGdAwk1jQpB1` |
| Drive run folder | `https://drive.google.com/drive/folders/1VWWQtajpXPs8E9lCBzQA9jvGG5dEgayK` |
| Final state | `succeeded` |

Metadata checks also read `1,519,950` documents from `homelab` and `49,229`
documents from `obsidian_vault`. Isolated restore evidence for PostgreSQL,
CouchDB and Couchloom is recorded in the [core audit](./2026-10-25-db-management-core-audit.md).

## Retention

The live db-management policy is `retentionDays: 7` and `localKeepRuns: 2`,
with empty include/exclude lists. Configuration and successful upload are
proven; deletion of an expired Drive object is not. No destructive retention
run was forced during this check.

## Databasus acceptance boundary

Databasus `v3.60.0` is healthy. Its logical/physical retention cleaners and
backup/restore schedulers started successfully. However, its storage and backup
APIs return `401 Authorization token required`; the inspected `67.6 MB` volume
showed local storage-test files and logs, not a completed Drive receipt.

Still unproven: authenticated account access, provider/storage configuration,
backup to Drive, remote retention deletion, and Databasus restore.

## UI and DNS checks

- CloudBeaver direct LAN route: HTTP `200`.
- CouchDB direct LAN route: HTTP `401 Authentication required`; the route and
  auth gate are alive.
- Pi5 AdGuard answers private names with `10.10.0.5`.
- The current workstation may resolve them to `103.82.21.202` through VPN DNS,
  producing a public 404/certificate mismatch even when the LAN service works.

## Credential and safety boundary

Credentials remain in Swarm secrets, local variable files or the password
manager. This vault records only secret names/locations. VM110 is an operations
worker, not a production datastore and not a separate Proxmox failure domain.
The db-management worker has no restore HTTP route.

## Open gates

1. Reconcile the migration manifest: migration/cutover tests pass, but the
   current parity verifier reports source/destination collisions and hash
   mismatches because the vault changed after the original copy. Refresh the
   reviewed manifest from the current source before declaring parity complete.
2. Publish the reviewed local `homelab-ops/main` commits to GitLab and run the
   protected CI validation before treating the merge as remotely accepted.
3. Authenticate Databasus and prove provider/storage configuration.
4. Capture one Databasus Drive backup receipt and one controlled restore.
5. Prove remote retention deletion with a disposable expired object.
6. Fix workstation split-DNS priority and verify routes without `--resolve`.
7. Retire old scripts/Semaphore consumers only after an authenticated inventory
   and replacement acceptance.

## Related records

- [Current status](../STATUS.md)
- [Current stack](../STACK.md)
- [DB-management project context](./2026-10-25-db-management-project-context.md)
- [DB-management core audit](./2026-10-25-db-management-core-audit.md)
- Ops migration evidence: `/home/dungxbuif/workspace/homelab-ops-task1/docs/migrations/2026-10-24-validation-evidence.md`
