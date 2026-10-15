# Runtime catalog reconciliation

Read-only Docker container/image/network observations on Pi5 and VM100 at
2026-10-15 show that the initial active policy still describes old networks.
Correct the policy before it becomes input for deployment automation. This
change must not attach/detach any running container or change public routes.
Mark the catalog incomplete, and distinguish verified restricted host audit
from unimplemented general apply access. Do not claim VPS enrollment exists.

Observed corrections: Semaphore is only on homelab-control-net; its runner is
on VM100 on that same network; provisioner is on control plus homelab-net.
Homepage is on edge-http-net. CouchLoom uses couchloom-internal (app also on
homelab-net), BDS app uses bds-tunnel-net plus homelab-net, and its Cloudflare
connector only bds-tunnel-net. KubeKosh actually uses homelab-net; LAN-only is
an exposure policy, not a Docker network name. Pi edge, datastore and registry
networks also need to match the observed Docker network names.

Verify policy parser, regression tests and declarative audit output; successful
validation must remain not_verified, not a statement of live service health.
Public app docs do not change because no public behavior changes.

VPS SSH preflight through alias gateway failed with agent signing communication
failure followed by too many authentication failures. The agent lists multiple
keys. Retry with only its existing Gateway public identity (private key remains
in 1Password), strict host trust, and IdentitiesOnly. This is diagnostic bootstrap
access, not production observer enrollment. Never change sshd or authentication
policy to bypass agent approval.

## Reconciled result

The policy now reflects the observed network corrections and includes the
previously missing Semaphore executor and BDS connector. `inventory_complete`
is explicitly false. Pi/VM100 list only their verified restricted capabilities;
VPS bootstrap and OpenTofu import remain pending instead of being presented as
deployed transports. No live network was changed.

Regression tests failed against the old Semaphore network, then passed after
the update in the pinned local execution image (4 tests). Policy validation
reports 5 hosts, 24 logical services, 8 routes, 3 backup classes and zero
Kubernetes infrastructure targets. The 5 inventory contract tests also pass
with 75 assertions. The first host-side test attempt additionally hit missing
PyYAML in its child interpreter; the execution-image run is the valid test.

This remains a partial catalog: additional VM100 apps and Pi monitoring/data
components observed during the audit still require individual ownership,
component and route reconciliation. Do not delete omitted resources or use
this file as a complete replacement deployment manifest.

## Expanded read-only inventory collection

Add a fixed `container_inventory` probe to the restricted host observer using
`docker ps -a --format` with explicitly selected ID, name, image, state, network,
port, Swarm service name and Compose project fields. Preserve existing probes.
Do not collect full inspect output, command arguments, environment, arbitrary
labels or secrets. JSON-lines formatting preserves exact string boundaries.
Deploy only the collector update through the existing enrollment playbook,
then gather Pi5/VM100 observations via Semaphore before reconciling missing
catalog entries. This remains metadata collection, not health certification or
permission to remove unowned containers. Test the selected field boundary and
run the existing observer suite before installation. No public docs change.

Collector rollout succeeded: Pi5 changed one helper task; VM100 changed the
helper and reconciled its existing exact observer sudo rule. Both playbooks
completed with zero failures. Semaphore tasks 26 (VM100) and 27 (Pi5), runner 1,
completed successfully and returned the new JSON-lines probe. Their playbook
checkout was dfc0aaf5; the separately enrolled collector update is recorded in
this change, not implied to be part of that earlier checkout.

The policy now contains 53 logical services/components, adding omitted VM100
apps, their private worker/datastore components, GitLab tunnel clients, and Pi
monitoring/admin components. Six observer tests and five policy tests pass;
the validator still reports zero Kubernetes infrastructure targets. The
`k8s-syntax` learning application is not a Kubernetes cluster: tests now check
host/class boundaries rather than excluding any app whose name contains k8s.

Observed image tags are evidence only, not approved deployment digests. Ports
shown as `80/tcp` by Docker are exposed container ports, not host publication.
AdGuard binds host 53 and 81; Alertmanager binds 9093; VictoriaMetrics binds
8428. The latter observations are marked for review, not added as approved
public ingress. No ports were closed or routes changed in this audit.

Outstanding data/ownership checks:
- CouchLoom PostgreSQL is on VM100, contrary to the intended Pi datastore role;
  assess a backed-up migration rather than silently accepting the placement.
- Pi `relayhub-relayhub-postgres-1` is running on `relayhub_relayhub`; establish
  current consumers before calling it retired or deleting it.
- Local backup inventory declares the shared Pi `postgres` only. Coverage of
  those two separate PostgreSQL instances is not proven; inspect live runner
  inventory and native exports before claiming all database instances backed up.
- VM100 `vigorous_napier` continues cycling Alpine tasks; owner/purpose is
  unknown. Stopped legacy containers and this service were not removed.
- Rootless CI daemon inventory, VPS/Mac observations, routes, owners and resource
  limits remain incomplete. Keep `inventory_complete: false`.

Live Pi runner inventory was subsequently read at
`/ssd-data/infra/backup-runner/app/backup/inventory.yaml`: its PostgreSQL host is
pi5 and container is `postgres`; CouchDB container is `couchdb`. Thus the current
database-class inventory does not enumerate the two extra PostgreSQL instances.
Do not extend the existing green database-class result into a claim that every
PostgreSQL instance in the lab is protected; separate export/migration evidence
for those instances is still required.

## Uncovered PostgreSQL instance safety checkpoint

Read-only native SQL on 2026-10-15 confirmed VM100 `couchloom-postgres`
contains `couchloom` (48,789,171 bytes) and `postgres` (7,657,139 bytes).
The application database has 13 pgboss tables and two public tables. Pi's
`relayhub-relayhub-postgres-1` contains `relayhub` (8,435,379 bytes) and
`postgres` (7,698,099 bytes). Database size is allocated logical storage,
not expected compressed dump size, and does not establish active consumers.

Before migration or retirement decisions, create a separate timestamped,
mode-0700 checkpoint directory on each source host. Use the matching container's
native `pg_dumpall --globals-only` and `pg_dump --format=custom` for each
non-template database, with restrictive umask, and validate every dump using
that container's `pg_restore --list`. Record checksums only after all commands
succeed. Never overwrite a previous checkpoint or print globals/password hashes.
No DB writes, app restart, network exposure, or production restore is involved.
These local checkpoints do not count as remote backup, restore rehearsal, or
automatic ongoing coverage; those gates remain outstanding. Public docs do not
change because this is internal data protection with no user-facing API change.

Checkpoint execution completed without production DB mutations:
- VM100: `/home/ubuntu/backup-checkpoints/couchloom-20261015T005416Z`,
  approximately 27 MiB, globals and custom dumps of couchloom/postgres.
- Pi5: `/home/dungxbuif/backup-checkpoints/relayhub-20261015T005426Z`,
  approximately 68 KiB, globals and custom dumps of relayhub/postgres.
- Both native `pg_restore --list` checks and SHA256SUMS verification passed.
  Additional `pg_restore --file=/dev/null` decoded both complete dump payloads
  per host successfully; this is stronger than catalog listing but still not
  a restore into a running isolated PostgreSQL instance.
- Source parents/checkpoint directories are private (0700, umask 077). Dumps,
  globals, and lists stay on source hosts, not in Git. No secrets were printed.
- Ongoing multi-instance discovery, remote upload and independent restore
  verification remain required. Retain these checkpoints until replacement
  remote protection is verified; do not let ordinary successful shared-PG
  backups imply permission to remove them.

Next verification: restore each checkpoint into a uniquely named disposable
container using the exact locally installed source image ID (no pull). Use
`--network none`, no published ports, tmpfs PGDATA, resource limits, and no
production mounts. Create a separate test superuser, restore globals with
ON_ERROR_STOP, then restore both custom dumps with exit-on-error. Compare
non-system table counts and run native SQL against the restored databases.
Remove only the exact disposable container after verification; preserve source
checkpoints. This proves an isolated local restore, not remote recovery.

### Independent local restore results

Both rehearsals passed on 2026-10-15 with 512 MiB memory/one CPU limits,
256 MiB tmpfs PGDATA, no published ports, and network mode `none`:
- CouchLoom test `homelab-restore-couchloom-20261015T005555Z`, exact image
  `sha256:cf134a767f474095eeba57e0117be8e568e011a63f33fbf252f14c9b760f8e6f`.
  Globals restored with ON_ERROR_STOP; both database dumps restored with
  exit-on-error. Restored schema counts match observed source counts:
  pgboss 13, public 2.
- RelayHub test `homelab-restore-relayhub-20261015T005607Z`, exact image
  `sha256:ff80089083d7365046af7f03d949a2defa14e0b09e14bd5b8f08a242291be8b2`.
  The same globals/dump checks passed; restored public table count is 14,
  matching the source.
- Cleanup removed only each newly created test container by captured container
  ID. Subsequent `docker ps -a` name filters returned no matching containers
  on either host. Production data/containers and checkpoints remain unchanged.

These are real local native restores, but not application-level acceptance or
recovery from Google Drive. Automatic backup inclusion and remote recovery
remain outstanding; no overall backup completion claim is warranted.

## Multi-instance backup implementation contract

Preserve the existing shared PostgreSQL manifest and provisioner inventory
shape. Add optional `postgresql_instances` entries with unique `id`, `host`,
`container`, `admin_user`, and `databases`. Each additional local instance gets
its own `instances/<id>/` subtree and adapter manifest; database names may
repeat across instances without overwriting dumps. Add coverage under
`postgresql_instances` only when configured. Any configured instance failure
must prevent COMPLETE and publication of the whole database run.

Validate the complete instance list before any export: reject malformed entries,
duplicate IDs/containers, unsafe IDs, and a host differing from the primary
PostgreSQL host. A remote instance must not accidentally execute against a
same-named local container. Cross-host CouchLoom export still needs a restricted
transport or migration to Pi; do not pretend this local adapter covers it.
Keep production inventory unchanged until deployment and native export checks.
Verify legacy compatibility, separate paths, failure atomicity and invalid-input
rejection with unit tests. Existing restore CLI can target an instance subtree
as its `--run-dir`. This is an incremental implementation of complete instance
coverage, not a replacement for cross-host backup or remote restore acceptance.

Implementation now passes five new tests, including actual adapter output
layout/checksum coverage with mocked native CLI. The full Python backup suite
passes 62 tests in `homelab-automation-ee:local`. Host Python lacked Jinja2 for
an existing scheduler test; only the execution-image full run is the valid
suite result. CI includes the new tests.

Review found that an empty database list could produce globals-only success;
an added regression failed first and now passes after rejecting empty lists
before any export. Invalid/option-like container names are also rejected.
Runtime inventory and installed runner remain unchanged. Before enrollment,
reconcile standalone inventory validation with the optional instance schema,
then verify the Pi instance export and remote snapshot. Cross-host CouchLoom
transport and complete multi-instance restore acceptance remain outstanding.

Validator reconciliation: move the additional-instance schema validation to
the existing shared helper module so offline validation and the live runner
use the exact same checks. Regress valid configuration, remote-host rejection,
duplicate IDs/containers, empty databases and malformed entries in the offline
validator. Preserve primary inventory behavior and verify the full suite before
deployment. No public interface changes beyond the documented optional schema.

Reconciliation completed: both entry points now call
`common.validate_postgres_instances`. The new offline regression failed in six
cases before the fix; all 63 Python backup tests now pass in the execution
image. Read-only review found no new blockers. This is source/CI readiness,
not deployment: active retention still owns the backup operation and runtime
inventory has not changed. Production enrollment and remote post-check remain
separate acceptance steps.

Instance enrollment must reuse the catalog's `.inventory.yaml.lock` and atomic
metadata-preserving JSON writer. Add an operator-only registration function
(not exposed by the public provisioner API): validate the optional schema,
append a new instance without changing any existing resource, treat exact
repeats as no-op, and reject same-ID drift. Accept only explicit metadata
fields, never credentials. Test conflict nonmutation, idempotence, catalog
preservation and file mode/ownership before using this to enroll production.

The operator registration helper is implemented and reviewed. It accepts only
the six instance fields and three database metadata fields; unexpected fields
at either level are rejected. An exact existing instance returns unchanged,
drift raises a conflict without writing, and updates use the same sidecar lock
as Semaphore's normal DB registration. All 66 Python backup tests pass in the
execution image, including a two-process mixed-writer test retaining both a
new DB and new instance, nested-secret rejection, and mode/owner preservation.
No public provisioner endpoint was added. Production enrollment remains pending.
