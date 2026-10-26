# DB Management Control Plane Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans or superpowers:subagent-driven-development to implement and verify one task at a time. Do not enable multiple schedule owners for the same source.

**Goal:** Provide one internal administration entry point and a verified, understandable backup inventory without rebuilding upstream backup engines.

**Architecture:** All new management services and heavy backup operations run on VM110 (DB Ops). Production data stays on Pi5; GitLab native export remains beside GitLab on VM100 through a restricted executor. Databasus owns PostgreSQL backup scheduling; Backrest owns other backup schedules after acceptance. The control plane consumes their state and invokes narrowly defined operations.

**Tech Stack:** Bun + TypeScript for custom backend, workers and tooling; React + TypeScript + Vite for UI; SQLite for local control-plane metadata; upstream containers for CloudBeaver, Databasus and Backrest; native database tools, Restic and rclone where required; Ansible for deployment.

**Spec:** [Approved transition and Drive destination](../../deployments/2026-10-23-backup-control-plane-transition.md).

**Status:** Plan only. Legacy timers have been disabled; replacement is not deployed. Live backup coverage must not be claimed until verified.

## Global Constraints

- Domain: `db-management.dungxbuif.com`; LAN and explicitly authorized NetBird clients only. HTTPS does not imply public accessibility.
- Management placement: VM110, `10.10.0.32`; no new management workloads on Pi5 or VM100.
- Existing Pi5 AdGuard/Traefik/Rathole remain unchanged except a narrowly scoped internal ingress route.
- Reuse Google Cloud project `homelab-backup-488616` and Drive root `1XzEaTjaBnDU0smPxuzkEnw5s2ScRn3OW`.
- Preserve existing snapshots and recovery keys. No recursive deletion at Drive root.
- No Redis/NATS backups. Preserve required GitLab config/secrets and separate object data.
- Daily backup baseline, timezone `Asia/Saigon`; discover and document existing retention before choosing changes.
- No application downtime for scheduled export. Online exports must state consistency limits.
- New custom JavaScript runtime is Bun, source is TypeScript, dependencies locked. Do not silently install Node.js as a fallback.
- Keep upstream applications' supported runtimes; do not port CloudBeaver, Databasus or Backrest to Bun.
- Secrets stay server-side in restricted files/secrets, not source, images, browser storage or job output.
- Commit only reviewed task files; preserve unrelated dirty work.

## Runtime Compatibility Gate

Use Bun for API, `bun test`, TypeScript worker execution and dependency installation. Type-check separately with `tsc --noEmit`; Bun executing TypeScript is not a type check.

- Test `nano` with the installed CouchDB version: authentication, pagination, errors and streaming.
- Test `@cloudant/couchbackup` under Bun against a disposable CouchDB. Upstream documents Node LTS support, not guaranteed Bun support. Cover export, restore, large streams, cancellation and resume before adoption.
- Attachments are an independent blocker: CouchBackup's attachment mode is experimental. Do not use it for attachment-bearing DBs solely because a simple export works.
- If Bun compatibility fails, retain the existing verified export path or use CouchDB-native replication into an isolated instance. Record the limitation; a Node runtime exception needs explicit approval.
- Use a tested S3 SDK/CLI for RustFS. Native CLI binaries such as pg_dump, Restic and rclone do not require replacing them with TypeScript implementations.

## Ownership and Deployment

| Component | Placement | Responsibility |
| --- | --- | --- |
| Control plane API/UI | VM110 container | Catalog, audit, unified backup views, notifications, authorized actions |
| CloudBeaver | VM110 container | SQL and database browsing through upstream UI |
| Databasus | VM110 supported deployment | PostgreSQL jobs, Drive storage, retention, verification |
| Backrest | VM110 container | Non-PostgreSQL backup plans, Restic repositories, retention |
| Export/verification worker | VM110 restricted container | CouchDB/RustFS export, payload validation, isolated restore |
| GitLab executor | Existing VM100 GitLab host | Fixed native export command, bounded status and artifact transfer |

Use separate internal tool hostnames (proposed `databasus.dungxbuif.com`, `cloudbeaver.dungxbuif.com`, `backrest.dungxbuif.com`), not iframe hacks or unsupported path prefixes. Tool authentication remains independent initially; no promise of shared SSO.

VM110 is not assumed to be a Swarm member. Inspect current topology before choosing Compose routing through a restricted private endpoint or an approved Swarm attachment. Docker DNS works only on networks the containers actually share. No public DB ports or broad homelab network attachment.

Keep web/API separate from privileged executors; never mount the Docker socket into the web container. Restore-verification tools needing container control require a dedicated restricted worker boundary. Budget resources after measuring VM110 disk headroom: initially one heavy export/restore at a time, bounded CPU/RAM/IO, and scratch-space preflight based on payload size.

## Storage, Retention and Recovery

Proposed children under the designated Drive root:

| Child | Owner |
| --- | --- |
| `databasus-postgres/` | Databasus only |
| `backrest-couchdb/` | Backrest/Restic only |
| `backrest-rustfs/` | Backrest/Restic only |
| `backrest-gitlab/` | Backrest/Restic only |
| `control-plane-recovery/` | Explicit recovery export workflow |

Validate Databasus can target the intended folder hierarchy before enabling it. A separate web OAuth client may be needed within the same project; do not assume an existing rclone refresh token can be imported. Keep OAuth consent/token lifetime suitable for unattended operation.

One retention owner per repository. Adopt current policy first, display actual expiry semantics, and test deletion only in a disposable repository. If a tool cannot enforce failure-gated retention, do not enable its destructive automatic cleanup until a compatible configuration is demonstrated. Keep a verified recoverable generation; incomplete jobs must not authorize deletion. Local staging cleanup runs only after remote validation, with active-job exclusions and bounded scratch TTL for abandoned runs.

Recovery bundle includes control-plane SQLite consistent backup, upstream catalogs/config, pinned versions and separately protected recovery secrets. Document bootstrap without a working control-plane instance. Do not rely solely on an encrypted repository to store its own decryption key.

## UI and API Contract

Views: Overview, Databases/Buckets, Backups, Schedules, Operations, Audit, Tool Links. Dense operational tables, readable GiB/MiB and local timestamps; no marketing landing page.

UI states distinguish: exported, uploaded, remotely verified, restore verified, failed, running, overdue, unknown/stale. Never turn provider failure into an empty successful inventory.

Canonical records:
- `Source`: id, kind, upstreamId, displayName, host, coverage, exclusions, ownerTool.
- `Backup`: id, sourceId, providerBackupId, startedAt, finishedAt, bytes, storageRef, stage, verification, expiresAt, errorSummary.
- `Schedule`: sourceId, ownerTool, timezone, expression, nextRunAt, enabled, observedAt.
- `Operation`: id, sourceId, action, idempotencyKey, state, requestedBy, timestamps, boundedError.

Adapters expose `listSources()`, `listBackups(sourceId)`, `getSchedule(sourceId)`, `getCapabilities()` and optional `requestBackup(sourceId, idempotencyKey)`. Unsupported mutation returns an explicit unsupported result and a link to the upstream UI. Do not scrape HTML, query upstream private databases or impersonate browser sessions.

Initial endpoints: `GET /api/sources`, `GET /api/backups`, `GET /api/schedules`, `GET /api/operations/:id`, `POST /api/sources/:id/backup`, `POST /api/backups/:id/verify`. Isolated restore is admin-only with an explicit target; in-place production restore and object deletion are out of MVP.

Use local admin/viewer roles, no public signup, secure HTTP-only sessions, CSRF protection, login throttling and audit. Backup credentials are read-only where possible; restore and provisioning credentials are separate. Generic SQL execution belongs in CloudBeaver, not the control-plane API.

## Proposed File Map

New application root (create only during implementation): `/Users/dungxbuif/workspace/db-management`.
- `src/server.ts`, `src/auth/`, `src/catalog/`: API, sessions, SQLite migrations.
- `src/adapters/{databasus,backrest,couchdb,rustfs,gitlab}.ts`: provider boundaries.
- `src/worker/`, `src/notifications/`: fixed operations, friendly Mezon summaries.
- `web/src/`: React operational UI.
- `tests/{adapters,worker,auth,notifications}/`, `tests/e2e/`: contracts and integration coverage.
- `docs/`, `public/llms.txt`, `openapi.yaml`: user/operator and agent-readable docs.

Homelab additions: `automation/db-management/compose.yml`, `automation/db-management/README.md`, `automation/ansible/playbooks/db-management-deploy.yml`. Update `docs/STATUS.md`, `docs/STACK.md`, `docs/runbooks/backup-restore.md` after each verified migration.

## Review Focus

- Provider API changes/stale responses must not fabricate coverage (Tasks 2, 6).
- Live CouchDB attachments/conflicts and S3 object mutations must not silently disappear (Tasks 3, 4).
- Retried requests, restart and failed exports must not upload stale payloads (Tasks 3, 6).
- Drive expiry/quota or full staging disk must preserve old recoverable backups (Tasks 2, 3, 7).
- Ingress source forwarding and executor privileges must not expose admin actions publicly (Tasks 1, 6).

## Task 1: Inventory, Cleanup and VM110 Foundation

- [ ] Inventory timers, cron, containers, repository owners, current policy and last verified backups on all three hosts. Record the paused-coverage interval prominently.
- [ ] List exact cleanup candidates and references; archive legacy definitions. Remove only verified inactive runtime/cache. Retain snapshots, secrets and rollback artifacts; no blind Docker prune.
- [ ] Measure VM110 resources and disk requirements; verify private data connectivity and current IaC inventory.
- [ ] Prepare locked deployment versions, restricted secrets, tool ingress and login.
- [ ] Verify LAN/NetBird authorized access and denial from public ingress, including forged forwarded headers. Verify service restart persistence.
- [ ] Record evidence and scoped commit. Do not wait for dashboard completion to restore backup coverage in later tasks.

## Task 2: Databasus PostgreSQL Pilot and Rollout

- [ ] Pin an upstream release; verify supported API/auth, backup format, Google Drive folder targeting and restore-verification requirements.
- [ ] Enroll one disposable DB with least-privilege backup access; use the designated OAuth project and test child folder.
- [ ] Test backup, remote read, isolated restore and representative rows/schema; test expired credentials and quota errors without deleting old backups.
- [ ] Prove roles/grants/extensions/globals recovery separately: per-DB dump is not a cluster recovery bundle. Record GitLab DB overlap intentionally.
- [ ] Add all approved PostgreSQL sources, list exclusions and enable daily schedules one at a time. Detect uncataloged new databases as a coverage warning; do not claim automatic enrollment without testing it.
- [ ] Verify retention in a disposable target, post-check behavior, notifications and API fixtures. If no suitable API exists, link the UI and expose only independently verifiable metadata.
- [ ] Publish evidence and scoped commit before moving on.

## Task 3: Backrest and CouchDB

- [ ] Verify Backrest supported interfaces, rclone repository access, hooks and failure propagation in the pinned release.
- [ ] Add tests where failed export, worker restart and duplicate invocation cannot back up yesterday's staging directory as a new successful run.
- [ ] Inventory CouchDB attachments, conflicts, design docs, security and system DB requirements. Test CouchBackup under Bun only on compatible disposable data.
- [ ] Select CouchBackup only if actual coverage and restore pass; otherwise keep a native replication/snapshot path. A replica alone is not retained history.
- [ ] Create a unique immutable staging run and manifest; fail closed if any DB export fails. Backrest snapshots only validated payloads.
- [ ] Restore to isolated CouchDB; compare documents, attachments and required metadata, plus representative LiveSync operation. Validate cancel/resume and large streams.
- [ ] Enable the daily plan after remote/restore verification, update coverage and commit.

## Task 4: RustFS

- [ ] Implement/export via supported CLI or S3 SDK, not live volume copying. Read-only backup credentials cannot delete source objects.
- [ ] Inventory bucket config, tags, user metadata, policies, versioning and encryption keys. Define whether all versions/delete markers or current versions are covered; expose exclusions.
- [ ] Test object overwrite/delete during export, pagination and multipart checksums. ETag is not assumed to be a content hash.
- [ ] Export version-addressed data where supported; otherwise detect changes and retry/fail. Do not claim bucket-wide atomic consistency.
- [ ] Snapshot verified payloads through Backrest and restore into a separate bucket. Verify content hashes and required metadata, then enable daily schedule and commit.

## Task 5: GitLab

- [ ] Reuse fixed-command executor on VM100; run supported native backup and separate config/secrets backup. Do not grant arbitrary SSH/shell from the web UI.
- [ ] Transfer completed artifacts to VM110 with manifest/checksum and exact GitLab version/edition; inspect external object storage and registry coverage.
- [ ] Test export timeout, interrupted transfer and insufficient disk. No incomplete artifact may be reported successful.
- [ ] Snapshot to its Backrest repository; perform an isolated supported-version restore with representative repository and artifact checks before marking restore verified.
- [ ] Enable daily schedule, publish coverage/exclusions and commit.

## Task 6: Bun/TypeScript Control Plane

- [ ] Scaffold locked Bun/TS application, SQLite migrations, admin/viewer auth and audit tests before implementing mutations.
- [ ] Implement provider contracts with recorded sanitized fixtures; test pagination, missing permissions, unsupported capability and stale upstream state.
- [ ] Implement UI views and links, distinguishing remote validation from restore validation. Keep upstream schedule editing in its owning tool.
- [ ] Add fixed-action dispatch with durable idempotency, per-source locks, timeout, restart reconciliation and bounded retries. UI cancellation must not orphan children.
- [ ] Verify SQL/command injection, SSRF via editable endpoints, CSRF, role boundaries and secret redaction. Browser must never receive provider credentials.
- [ ] Run `bun test`, `bunx tsc --noEmit`, production build and Playwright desktop/mobile navigation tests. Test API outage and worker restart end to end.
- [ ] Commit verified app and IaC separately; do not commit secrets.

## Task 7: Notifications, Recovery and Acceptance

- [ ] Consolidate Mezon delivery server-side. One daily summary listing covered DBs/buckets and understandable failures; no successful health spam. Deduplicate retries and tool notifications.
- [ ] Test webhook failure with retry/outbox behavior; notification failure must not erase a successful backup or hide an unsuccessful one.
- [ ] Verify retention and local cleanup with expired, active, incomplete and last-good generations. Test full disk and Drive authentication failure.
- [ ] Restore the control-plane catalog/config from recovery bundle without the original VM; document separately held recovery keys.
- [ ] Update operator runbooks, beginner UI guide, OpenAPI and `llms.txt`; clearly state backup formats, scope, known consistency limits and manual recovery.
- [ ] Observe one complete scheduled daily cycle in addition to manual tests. Report each class after it passes; incomplete classes remain visible as not protected.
- [ ] Final scoped review/commit and reconcile STATUS/STACK. Never call the whole stack ready based only on green upload jobs.

## Deferred Scope

No replacement SQL editor, full S3 browser, automatic production restore, PITR rollout, new storage destination or general shell runner. Simple DB-and-user provisioning can follow backup acceptance through the existing reviewed Ansible workflow; it must also enroll or flag the new source for backup.

## Sources and Evidence Limits

- https://github.com/databasus/databasus
- https://databasus.com/storages/google-drive/
- https://github.com/garethgeorge/backrest
- https://github.com/IBM/couchbackup
- https://github.com/apache/couchdb-nano
- https://docs.couchdb.org/en/stable/maintenance/backups.html
- https://docs.gitlab.com/administration/backup_restore/backup_gitlab/
- https://docs.rustfs.com/en/

Repository feature descriptions are not proof of compatibility with the deployed versions. API, Bun and restore gates above are mandatory before production adoption.
