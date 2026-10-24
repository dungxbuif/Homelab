# DB management and operations repository design

## Intent and decisions

User requirements agreed in the 2026-10-24 conversation: an internal entry point
for database administration and backups; good existing tools remain first-class
bookmarks. Integrate supported APIs/metrics when useful. Implement missing basic
administration through backend adapters. New database types must be extensible.
Architecture details are delegated to the implementer.

Frontend: React, TypeScript, Vite and shadcn/ui. Custom backend and worker:
NestJS and TypeScript running on Bun. Use a single Bun-workspaces monorepo at
`/home/dungxbuif/workspace/db-management`, with a private GitLab project proposed
as `dungxbuif/db-management`; verify authenticated namespace before creation.
Compile NestJS with TypeScript decorator metadata; do not assume Bun's direct
TypeScript execution provides the metadata Nest dependency injection needs.
Pin versions after a working integration spike. No silent Node runtime fallback.

VM110 joins the existing Swarm as a worker. New management services execute on
VM110 using placement constraints. Production databases remain on Pi5. GitLab
native export stays on VM100 via a restricted executor. Infrastructure changes
and deployment definitions belong to `homelab-ops`.

## Product scope

- Basic CouchDB administration: list databases, size/status, create database,
  inspect/update database membership. Use Fauxton links for document editing.
- PostgreSQL: CloudBeaver/tool bookmarks are useful complete integrations;
  add supported metrics/API capabilities only after checking pinned releases.
- Backup inventory, schedule visibility and authorized backup requests.
  Databasus is the PostgreSQL candidate; Backrest/Restic owns other schedules.
  Provider support must be proven, never fabricated by scraping private state.
- Automatic verification: payload integrity, remote readback, and isolated
  engine restore drills are distinct evidence levels with their own timestamps.
  No user-facing restore action, production restore endpoint or object deletion.
- Overview, Sources, Backups, Schedules, Operations, Audit, Tool Links; show
  failed, running, overdue, unsupported and stale states honestly.
- Local admin/viewer accounts; no public signup. Secure HTTP-only sessions,
  CSRF protection, throttled login, server-side secrets and audit of mutations.

## Architecture selected by implementer

Use an in-process registry of typed database adapters and backup providers.
A single combined adapter would couple administration to a backup vendor;
dynamically loaded plugins would add an unnecessary deployment/security surface.
Separate capability contracts permit bookmarks, metrics, administration and
backup support independently. Unknown adapters fail explicitly.

`apps/web` contains UI, `apps/api` the NestJS HTTP app, `apps/worker` a NestJS
application context for durable work. `packages/contracts` defines shared runtime
schemas; `packages/adapters` integrates tools; `packages/storage` owns SQLite
migrations, transactional job claims and catalog persistence. Start with one API
and one worker on VM110 sharing a local SQLite volume, WAL and bounded busy
timeouts. Test concurrent access and crash recovery. This is not multi-node HA.

Workers use durable idempotency, leases/fencing, bounded retries and per-source
locks. Permit one heavy operation globally initially. A lease expiry cannot
authorize duplicate side effects while an old process still runs; reconcile
executor/provider state before retrying uncertain operations.

Only a restricted verification executor can create disposable restore targets;
the API has no Docker socket or arbitrary command facility. Verification jobs
cannot select production destinations. Keep provider secrets out of API output,
browser storage, logs, Git and image layers.

## Backup acceptance and preservation

Follow the transition record of 2026-10-23. Legacy schedules are documented as
disabled; coverage remains paused until fresh per-source evidence establishes
otherwise. Inventory live timers, cron, containers, sources and last good runs.
Do not postpone restoring verified coverage until the dashboard is finished.

Reuse Google project `homelab-backup-488616`, Drive root
`1XzEaTjaBnDU0smPxuzkEnw5s2ScRn3OW`, and separate provider-owned child folders.
One scheduler and one retention owner per source/repository. Baseline policy
from `backup/policies.yaml`: daily 14, weekly 8, monthly 12, restore drill every
30 days; confirm live policy before applying. Timezone `Asia/Saigon`.
If a provider cannot preserve these semantics, expose the limitation and keep
destructive retention disabled until an equivalent policy is agreed.

Reuse behavior in `backup/scripts/verify-database-payload.py`,
`automation/backup-runner/run-restore-drill.sh`, and engine restore scripts.
The existing scheduled drill restores payload files and validates manifests and
checksums; it is not proof that the database engine can restore them. Add engine
restore verification with representative data/schema checks. Verify PostgreSQL
globals/extensions, CouchDB attachments/conflicts/security/LiveSync metadata,
RustFS object metadata/version exclusions, and GitLab version/config/secrets.
Failures must preserve previous recoverable backups. Never validate stale staging
as a new run. Keep snapshots, keys and last-good artifacts during migration.

## Repository boundaries and migration

User additionally requests all code in `homelab` moved to `homelab-ops`, organized
with complete documentation and reciprocal references. Include active scripts,
tests, manifests, IaC, embedded source and historical code, preserving provenance.
Keep infrastructure knowledge, operational history and dated evidence in
`homelab`; code-local READMEs and executable instructions travel with code.
Existing standalone app repositories are not moved into ops; embedded copies
are inventoried as snapshots with references to their authoritative repositories.
New `db-management` remains its own application monorepo.

Secrets (`local_vars.json`, `credentials/`), Terraform state, caches and machine
configuration are excluded from committed migration payloads. Inventory their
path dependencies separately and provide explicit private configuration paths.
Both repos contain pre-existing dirty changes; preserve them and record hashes
before any relocation. Never overwrite colliding destination files blindly.
Migrate consumers before removing source copies. Archive old Kubernetes code as
historical and prevent active CI/discovery from treating it as production.

## Evidence and limitations as of planning

- Local GitLab bootstrap token returned HTTP 401; ownership/admin status unproven.
- Public GitLab login returned 200 with valid TLS. This does not prove login or
  repository operations work, and the user's browser problem is unresolved.
- No browser automation tool was available during discovery. Do not claim a
  credential was created. Inspect scoped local credential metadata safely next.
- Local `homelab-ops` exists at `/home/dungxbuif/workspace/homelab-ops` and contains
  historical Kubernetes/ArgoCD configuration plus dirty edits, not a verified
  Swarm deployment workflow.
- VM110 capacity, Swarm connectivity, provider API compatibility and Drive access
  require execution-time checks. No runtime migration is claimed by this design.

## Non-goals

SQL editor replacement, document editor replacement, public administration,
PITR, a new storage destination, production restore UI, arbitrary shell runner,
dynamic plugin marketplace and infrastructure-wide behavior refactoring.

## Acceptance

Code ownership and cross-references resolve in both repositories; ops CI and
actual deployment consumers use the new paths. The monorepo builds/tests under
Bun, new adapters do not require core conditionals, private ingress and roles
are verified, and each enrolled source completes backup plus independent remote
and restore verification. Observe one daily scheduled cycle and prove the
30-day drill registration with a manual invocation of that same job path.
