# DB Management Monorepo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver an extensible private DB administration hub with verified backups on VM110, deployed through homelab-ops.

**Architecture:** Bun-workspaces monorepo with NestJS API/worker, React/shadcn UI and typed capability adapters. Ops owns Swarm infrastructure; provider tools own their backup schedules; the application records evidence and exposes supported operations.

**Tech Stack:** Bun, TypeScript, NestJS, React, Vite, shadcn/ui, SQLite, Docker Swarm, Ansible; CloudBeaver, Databasus, Backrest/Restic subject to compatibility gates.

**Spec:** `../specs/2026-10-24-db-management-design.md`

## Global Constraints

- A = `/home/dungxbuif/workspace/db-management`; O = `/home/dungxbuif/workspace/homelab-ops`; H = this homelab vault.
- This plan supersedes the 2026-10-23 control-plane plan's application layout and Compose-only assumptions. Preserve its backup transition evidence and recovery safeguards.
- First execute the companion `2026-10-24-homelab-ops-code-migration.md` for code ownership; app-local tasks may run while its remote cutover is pending.
- Custom services run NestJS/TypeScript on Bun; upstream tools keep supported runtimes. Lock dependencies and deployment digests after compatibility checks.
- VM110 (`10.10.0.32`) joins the existing Swarm as worker; never initialize a competing cluster. Pi5 remains data host/manager.
- `db-management.dungxbuif.com` and tool ingress are LAN/authorized-NetBird only. Pi5 file-provider routing is the existing ingress mechanism.
- No public signup, production restore UI/endpoint, arbitrary shell executor or Docker socket in the API.
- One scheduler/retention owner per source, daily baseline, timezone `Asia/Saigon`; retain 14 daily/8 weekly/12 monthly and 30-day restore drills subject to live-policy reconciliation.
- Preserve snapshots, keys and last-good artifacts. Report coverage paused/unverified until acceptance.
- GitLab token currently returns 401; no browser-control tool was discovered. Do not claim project/credential creation without evidence; local work remains possible.

## Review Focus

- Provider outage or unsupported API looks like healthy empty inventory: Task 3 tests explicit stale/unsupported results.
- Lease expiry/restart duplicates backups or uploads old staging: Task 5 tests reconciliation and fencing.
- Restore verifier reaches production or loses attachments/object metadata: Task 6 tests destination isolation and representative payloads.
- Swarm replacement loses SQLite or overlays leak admin ingress: Tasks 2/8 test persistence and access boundaries.
- App/ops CI uses mismatched revisions or secrets appear in build artifacts: Task 9 tests provenance and scans.

## File structure

In A: root `package.json`, `bun.lock`, `tsconfig.base.json`, `.gitignore`, `.gitlab-ci.yml`, `README.md`.
`apps/api/src/{main.ts,app.module.ts,auth/,sources/,backups/,operations/}` owns HTTP services.
`apps/worker/src/{main.ts,worker.module.ts,dispatcher.ts,reconcile.ts,verification.ts}` owns jobs.
`apps/web/src/{app.tsx,components/ui/,features/{overview,sources,backups,schedules,operations,audit,tools}/}` owns UI.
`packages/contracts/src/{adapter.ts,backup.ts,operation.ts}` owns runtime schemas/types.
`packages/adapters/src/{registry.ts,bookmark.ts,couchdb.ts,databasus.ts,backrest.ts}` owns integrations.
`packages/storage/src/{database.ts,migrations/,catalog.ts,jobs.ts,sessions.ts}` owns SQLite access.
`tests/{runtime,auth,adapters,jobs,verification}/`, `tests/e2e/`, `docker/{api,worker,web}.Dockerfile`, `docs/{operator,adapters,recovery}.md`, `openapi.yaml`, `public/llms.txt`.
In O: `automation/ansible/playbooks/{db-management-preflight,db-management-swarm-join,db-management-deploy}.yml`, `automation/stacks/db-management/stack.yml`, `automation/stacks/db-management/versions.lock.json`, `automation/tests/test_db_management_deploy.py`, routes catalog entries and CI jobs.

## Shared interfaces

`Capability = 'link' | 'status' | 'list-databases' | 'create-database' | 'permissions' | 'metrics' | 'backup-list' | 'backup-request' | 'schedule-read'`.
`Result<T> = {status:'ok',data:T,observedAt:string} | {status:'unsupported'|'unavailable'|'stale',reason:string,toolUrl?:string}`.
`Connection` has `id`, `adapterId`, configured endpoint reference, server-only `secretRef`, and optional allowlisted `toolUrl`.
`Source` has `id`, `connectionId`, `upstreamId`, `kind`, `name`, `ownerTool`, `coverage`, `exclusions`.
`DatabaseAdapter` exposes `capabilities(): Capability[]`, `listSources(connection): Promise<Result<Source[]>>`, `status(connection): Promise<Result<Health>>`; optional `createDatabase(connection,input)` and `setPermissions(connection,input)` return `Result<Source>`/`Result<void>`.
`BackupProvider` exposes `capabilities()`, `listBackups(source): Promise<Result<Backup[]>>`, `getSchedule(source): Promise<Result<Schedule>>`, optional `requestBackup(source,idempotencyKey): Promise<Result<ProviderJob>>`.
`Health` has `state`, optional `bytes`, and observation time. `Schedule` has owner, expression, timezone, enabled, nextRunAt, observedAt. `ProviderJob` has id/state.
`Backup` carries source/provider IDs, runId, timestamps, byte count, storage reference and independent verification evidence. `Verification` has backupId, level (`payload`/`remote`/`restore`), status, checkedAt and bounded evidence reference.
`Operation` has id/sourceId/action/idempotencyKey/state/requestedBy/leaseUntil/fencingToken/timestamps/boundedError. States: queued, running, reconciling, succeeded, failed, cancelled. Uncertain external state stays reconciling.
`AdapterRegistry.resolve(id): DatabaseAdapter`; `ProviderRegistry.resolve(id): BackupProvider`; unknown IDs throw a typed configuration error. Validate all inputs at HTTP/provider boundaries; UI consumes public DTOs without secretRef.

### Task 1: Monorepo and NestJS/Bun compatibility

**Files:** root manifests, API/worker bootstraps, contracts schemas, tests/runtime/nest-bun.test.ts, docs/compatibility.md.
**Interfaces:** Produces `createApp(): Promise<INestApplication>`, worker application context, shared contracts and scripts `test`, `typecheck`, `build`.

- [ ] Check A existence before creating it; preserve existing files. Inspect official NestJS/Bun docs and choose exact versions through a disposable compile/runtime spike.
- [ ] Write runtime integration tests asserting injected service resolution, validation error 400, health 200, SQLite write/read, worker boot and graceful shutdown under Bun. Run `bun test tests/runtime`; expected RED before bootstrap implementation.
- [ ] Implement Nest compilation with decorator metadata, workspace dependency boundaries and locked dependencies. Keep compiler and runtime checks separate; do not substitute Node if compatibility fails.
- [ ] Run `bun install --frozen-lockfile && bun test tests/runtime && bun run typecheck && bun run build`; expected all pass and built API/worker run with Bun. Record exact versions and invocation.
- [ ] Commit scoped scaffold/contracts and compatibility evidence.

### Task 2: Persistence, auth and catalog

**Files:** storage database/migrations/catalog/sessions, API auth/sources, tests/auth/session.test.ts, tests/runtime/storage.test.ts.
**Interfaces:** `openDatabase(path)`, `Catalog.listSources()`, `SessionService.authenticate(request)`, migrations with version ledger; consumes Task 1 DTOs.

- [ ] Write tests for admin/viewer boundaries, CSRF rejection, throttled login, expiry/logout, no public signup, redacted DTOs, concurrent API/worker SQLite access and catalog persistence after restart.
- [ ] Run `bun test tests/auth tests/runtime/storage.test.ts`; expected RED for missing behavior.
- [ ] Implement session hashing, secure cookies, password hashing, parameterized SQL, WAL/busy timeout and source catalog. Endpoint registration is operator-configured; reject arbitrary browser-supplied URLs and secret references.
- [ ] Run the same tests and `bun run typecheck`; expected PASS. Verify migrations cannot silently discard existing metadata.
- [ ] Commit auth/catalog implementation and tests.

### Task 3: Adapter registry and basic administration

**Files:** adapters registry/bookmark/couchdb/databasus/backrest, API sources controllers, tests/adapters/*.test.ts.
**Interfaces:** Implements shared DatabaseAdapter/BackupProvider contracts; all unsupported capabilities remain explicit.

- [ ] Write tests: bookmark adapter supplies link without pretending to have metrics; unknown ID fails; provider timeout is unavailable; stale data retains observedAt; paginated CouchDB sources are complete; malicious DB names rejected; viewer cannot create DB/change permissions.
- [ ] Run `bun test tests/adapters`; expected RED.
- [ ] Implement registries, bookmark and CouchDB adapters using tested HTTP/SDK calls. Preserve CouchDB roles/members during bounded membership updates; no blanket admin credential exposure or document editor.
- [ ] Inspect pinned provider documentation/source for public API/auth. Capture sanitized fixtures; implement supported read capabilities, otherwise return unsupported with tool link. Never scrape UI/private DBs.
- [ ] Run `bun test tests/adapters && bun run typecheck`; expected PASS. In disposable CouchDB, create/list a database and verify allowed/denied access for test users; destroy only that fixture.
- [ ] Commit adapters and API contract docs.

### Task 4: VM110 and backup-provider pilot through ops

**Files:** O preflight/join/deploy playbooks, stack.yml, versions.lock.json, deployment tests, route catalog.
**Interfaces:** Produces verified VM110 worker placement and provider endpoints consumed by adapter config; secrets are references only.

- [ ] Inventory actual Swarm membership, VM110 disk/RAM, private connectivity, all backup schedules, last-good artifacts and existing live retention; record paused coverage and exact cleanup candidates. Archive definitions before any approved bounded cleanup.
- [ ] Write deployment tests asserting worker join only if unjoined, foreign-cluster rejection, no manager promotion, VM110 constraints, no API socket, no public port exposure and private secret mounts. Run `python3 -m unittest discover -s automation/tests -p test_db_management_deploy.py` in O; expected RED.
- [ ] Implement idempotent worker enrollment via restricted ops workflow, constrained service definitions and internal ingress. Run Ansible syntax/check and `docker stack config -c automation/stacks/db-management/stack.yml`; expected valid/no unintended changes. Validate manager/worker connectivity before applying join.
- [ ] Deploy pinned upstream tools through O after compatibility checks. Verify private access, public denial and forged forwarding-header denial; restart a tool and prove config persistence.
- [ ] Enroll one disposable PostgreSQL database in Databasus, test Drive child-folder targeting, quota/auth failure, remote readback and isolated restore including grants/extensions/globals scope. Never assume an rclone token can be imported.
- [ ] Enable accepted production PostgreSQL sources one at a time; record exclusions and coverage warnings for new unregistered DBs. Backup coverage can resume before custom UI completion. Commit ops definitions and evidence.

### Task 5: Durable backup execution and scheduling observations

**Files:** storage/jobs.ts, worker dispatcher/reconcile, API backups/operations, tests/jobs/dispatch.test.ts.
**Interfaces:** `enqueue(sourceId,action,idempotencyKey,actor): Operation`, `claim(workerId): Operation|null`, `reconcile(operation): Promise<Operation>`; external request dedup keyed by source/action/key.

- [ ] Write tests for duplicate requests, per-source exclusion, one-heavy-job global bound, worker crash, expired lease with still-running child, timeout/cancellation, stale staging and provider unsupported mutation.
- [ ] Run `bun test tests/jobs`; expected RED.
- [ ] Implement transactional claims with fencing and durable provider job IDs; reconcile uncertain jobs before retry. Snapshot immutable run-specific staging only after manifest completion; UI cancellation cannot orphan children.
- [ ] Implement GET sources/backups/schedules/operations and POST source backup with admin/CSRF checks. Schedules are observed from owner tools; do not add a competing backup scheduler.
- [ ] Run `bun test tests/jobs tests/auth && bun run typecheck`; expected PASS. Crash/restart worker during a disposable backup and prove one external run.
- [ ] Commit dispatcher and operations endpoints.

### Task 6: Automatic verification and remaining backup classes

**Files:** worker/verification.ts, tests/verification/{payload,remote,restore,retention}.test.ts, O restricted executor definitions, migrated backup helpers.
**Interfaces:** `verifyBackup(backupId,level): Promise<Verification>` selects executor-created disposable targets; users cannot supply restore destinations. Separate internal drill scheduler owns verification only.

- [ ] Write tests for wrong run ID, missing/extra artifact, symlink/path traversal, checksum mismatch, incomplete marker, remote corruption, out-of-space, expired Drive credentials and restore attempts against a production endpoint. Assert failures never advance another evidence level or authorize retention.
- [ ] Run `bun test tests/verification`; expected RED.
- [ ] Reuse audited verifier behavior and fixed native-tool argument arrays; never interpolate a shell command from API input. Build restricted ephemeral restore executor with resource limits, isolated networks, TTL and cleanup excluding active runs.
- [ ] Gate CouchDB export choice on Bun compatibility and attachment/conflict/security/design-document coverage. Compare isolated restored content and LiveSync behavior; retain verified native path if CouchBackup cannot satisfy coverage.
- [ ] Test RustFS mutations during export, pagination, real content hashes, user metadata and declared version/delete-marker exclusions; restore into a separate bucket. GitLab uses its VM100 fixed executor and exact-version isolated restore with config/secrets and representative repository/artifact checks.
- [ ] Run all verification tests; expected PASS. Execute real remote-read and isolated-restore acceptance for each class before enabling its Backrest schedule. Preserve failure evidence and prior backups.
- [ ] Register daily verification/readback policy and 30-day engine drill, then invoke the exact scheduled entrypoint manually. Test retention only in disposable repositories; cleanup must preserve active/incomplete/last-good generations. Commit evidence and implementations.

### Task 7: shadcn administration UI

**Files:** apps/web features/components, tests/e2e/admin.spec.ts, tests/e2e/backups.spec.ts.
**Interfaces:** Consumes public API DTOs, capability lists and verification evidence; no provider credentials in browser.

- [ ] Write Playwright tests for bookmark navigation, supported/unsupported controls, CouchDB creation/membership, viewer restrictions, stale/provider-error states, backup request progress and distinct verification levels. Assert no restore control is present.
- [ ] Run `bun run test:e2e`; expected RED before screens exist.
- [ ] Implement shadcn tables/forms/dialogs with React, readable local timestamps/GiB, accessible error/loading/empty states and navigation. Keep provider-owned schedule editing linked to its tool.
- [ ] Run `bun run test:e2e && bun run typecheck && bun run build`; expected PASS on desktop/mobile, keyboard navigation and API outage cases.
- [ ] Commit UI and tests.

### Task 8: Application Swarm release, notifications and recovery

**Files:** Dockerfiles, O stack/deploy workflow, worker notification service, docs/recovery.md, tests/jobs/notifications.test.ts.
**Interfaces:** Release manifest `{appCommit,opsCommit,images:{api,worker,web},schemaVersion}`; SQLite remains one local VM110 volume shared by constrained services.

- [ ] Write notification tests for durable outbox/retry/dedup and backup success surviving notification failure. Run `bun test tests/jobs/notifications.test.ts`; expected RED.
- [ ] Implement one daily Mezon summary plus meaningful failures; no healthy-check spam. Add consistent SQLite recovery export, upstream config/catalog and separately held key instructions.
- [ ] Build immutable images, scan artifacts for secrets, deploy via O with resource limits/healthchecks and stop-first updates for services sharing persistent state. Verify API session/catalog persistence and worker reconciliation after replacement.
- [ ] Run private LAN and actual authorized NetBird peer probes; reject public ingress and forged headers. If no remote peer exists, record that acceptance as pending rather than infer it from LAN.
- [ ] Restore recovery bundle to disposable storage without the original catalog and exercise read-only API. Check schema rollback compatibility before permitting deployment rollback.
- [ ] Run relevant tests and health probes; expected PASS. Commit release manifest, tested recovery runbook and evidence.

### Task 9: GitLab provisioning, CI and final acceptance

**Files:** A .gitlab-ci.yml/README/docs/openapi.yaml/public/llms.txt, O CI/release docs, H status/index/project references.
**Interfaces:** Private A repository, immutable build artifacts, O-controlled deploy manifest, reciprocal documentation links.

- [ ] This prerequisite can run earlier: inspect local credential metadata safely, validate `/api/v4/user`, namespace and scopes. If a browser session/tool becomes available, create a named expiring token with minimum required access and store it in an ignored 0600 file. Do not print it, reset an account password or claim 401 proves an outage.
- [ ] Create or reuse private `dungxbuif/db-management` after identity confirmation; verify clone/push. Set protected/masked CI variables via supported API/UI and validate they never enter logs. Existing homelab-ops repo remains separate.
- [ ] Configure test/typecheck/build/image publication on app CI and scoped release through O. Pin app and ops revisions, serialize deployments and test rejection of unapproved image references and wrong-revision manifests.
- [ ] Run `bun install --frozen-lockfile && bun test && bun run typecheck && bun run build && bun run test:e2e` in A, O deployment validation and the migration plan's final audit. Expected PASS with actual evidence; report any existing failures by name.
- [ ] Observe one real daily cycle per enabled source, remote verification and manual invocation of scheduled restore drill. Check dead-man detection for a deliberately stale synthetic source. Pending classes remain visibly unprotected.
- [ ] Update both repos' docs and H status/stack/backlog with links to A/O, actual coverage, known limits, adapter extension example, credential recovery and exact tested revisions. Review changes independently where tools permit, then commit scoped work.

## Execution and review

Use native inline execution unless a different method is requested; it fits the
shared contracts and lets infrastructure gates block only dependent tasks.
Read the migration companion first. Maintain separate progress ledgers for both
plans. Do not declare the complete system ready until repository migration,
authenticated GitLab operations, deployment and backup acceptance all have evidence.

Plan self-review: requirements mapped to Tasks 1–9 and migration Tasks 1–4;
shared contract names aligned; five review risks assigned tests; no runtime or
provider capability is assumed verified. The earlier plan is historical input,
not a second active deployment source.
