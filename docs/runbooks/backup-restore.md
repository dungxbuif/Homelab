# Homelab Backup and Restore Runbook

**Status:** Online adapters, encrypted Drive upload, and the replacement VM100
backup flow are deployed, with historical class markers and restore evidence.
The 2026-10-31 live audit found the `homelab-backup-*` systemd timers
`disabled/inactive`; recurring execution is therefore not currently accepted
as active. Database, RustFS, GitLab, and configuration artifacts remain
documented as separate classes, while GitLab is intentionally excluded from
the current upgrade/backup wave. The `configs` class passed Restic integrity
verification and a local-mirror scratch restore with checksum verification. The legacy
`/ssd-data/backup/simple-backup.sh` cron entry was disabled on the Pi on
2026-10-05; its script and historical local artifacts remain for rollback and
audit until the replacement flow is fully verified.
**Owner:** Homelab operator  
**Timezone:** `Asia/Ho_Chi_Minh`

## Scope

This runbook covers five independent backup classes:

1. PostgreSQL and CouchDB databases on Pi5.
2. GitLab CE application data on VM100.
3. RustFS buckets and objects on Pi5.
4. Additional cataloged PostgreSQL instances on VM100.
5. Selected Pi5 and VM100 configuration sources.

Redis and NATS are deliberately excluded from the generic database class. Redis
has a separate RDB/AOF service procedure; the 2026-10-31 Pi5 pre-upgrade
snapshot and scratch restore are recorded in the controlled upgrade ledger.
NATS remains excluded. The generic database backup does not include application
files, Git repositories, uploads, artifacts, or object storage. GitLab and
RustFS have separate native/object-aware workflows because their recoverable
data is not database-only.

Catalog entries marked `retired` are retained for audit history but are not
exported. New manifests record those exclusions explicitly; system databases
needed for recovery remain covered.

## Operating Principles

- Prefer the native CLI or API supplied by the application.
- Scheduled backups run while production services remain available.
- Never copy a live database or RustFS data volume with `rsync`.
- `rsync` may be used only for an explicitly approved, stopped RustFS cold
  snapshot and is not part of the recurring schedule.
- Every backup class has an engine-specific post-check.
- A class is reported successful only after local validation, remote snapshot
  verification, and manifest/checksum validation pass.
- The engine manifest is immutable after export. The repository-specific
  snapshot ID is written to `remote/snapshot-id` after the upload and is
  passed explicitly to the post-check; the scheduler ID is written to
  `remote/run-id` so nested output directories cannot hide job identity.
- A failed class never triggers retention deletion.

## Backup Classes

### PostgreSQL and CouchDB

The database runner executes native logical exports online:

- PostgreSQL: one `pg_dump` custom archive per database and one
  `pg_dumpall --globals-only` export for roles/grants/globals.
- CouchDB: online replication/HTTP export with system/security metadata recorded
  in the manifest.
- Redis is not queried or exported by this generic class; use the separate
  RDB/AOF procedure for Redis service maintenance.

Post-check requirements:

- all required targets have a successful export;
- archive/list validation succeeds;
- checksums match;
- the remote restic snapshot exists and is readable;
- `remote/snapshot-id` identifies that verified snapshot;
- the manifest lists every covered database.

### GitLab

Run inside the healthy Omnibus GitLab container:

```bash
gitlab-backup create
```

Run the supported configuration/secrets backup separately. The GitLab workflow
must record the exact GitLab version and edition and must not stop the service.
The current lab uses local filesystem storage for the bundled Registry, so the
native backup covers its supported local data. If GitLab later uses RustFS or
another object store, that object store becomes an additional required backup
class.

Redis DB 2 is not part of this workflow. Sessions, cache, and Sidekiq queues
are expected to rebuild after restore; Redis service-level recovery is tracked
by its separate RDB/AOF procedure.

Post-check requirements:

- archive exists and is non-empty;
- archive version/edition matches the current instance;
- GitLab backup output completed without errors;
- config/secrets artifact exists without logging contents;
- the remote snapshot is readable;
- an isolated restore rehearsal has passed before production recovery is
  considered available.

### RustFS

Use the RustFS `rc` client or S3-compatible API to export approved buckets while
RustFS remains online. Record object keys, sizes, checksums/ETags, available
version IDs, and bucket metadata in the manifest. Restic snapshots preserve
historical exports on Google Drive.

Do not copy the live `/data` volume. A cold `rsync` copy is a break-glass
procedure only:

1. obtain explicit approval;
2. stop writes and stop RustFS cleanly;
3. copy all required data/config paths with ownership and metadata preserved;
4. record the exact RustFS version and volume topology;
5. restore into an isolated target and verify object checksums;
6. remove the cold-copy exception from the recurring schedule.

Post-check requirements:

- every approved bucket completed;
- manifest/object counts are present;
- checksums/ETags pass for the verification sample or full export;
- remote snapshot is readable;
- one selected bucket/object set restores into an isolated RustFS target.

### Host configurations

The `configs` class combines two explicit, fail-closed inventories into one
atomic encrypted Restic run:

- Pi5 edge and stack configuration: Traefik, AdGuard, Rathole, and selected
  Compose/env files;
- VM100 application declarations and selected environment/config files.

It excludes database volumes, backup staging, build caches, old releases, and
source/data directories. The Pi exporter preserves root-owned AdGuard files by
using the existing `alpine:3.22` image with `--network none`; it does not
change file permissions or mount the Docker socket. Staging is mode `0700`,
selected files are mode `0600`, and the collector refuses a missing required
source or an unsafe archive member.

The class is accepted only after Restic upload, remote post-check, and a
scratch restore. Historical acceptance passed, but its VM100 timer is currently
disabled; re-enable and verify the schedule before treating recurring execution
as active. The latest acceptance is recorded in
`docs/deployments/backup-configs-readiness-2026-10-20.md`.

![Backup and restore ownership flow](../assets/diagrams/data-and-backup.svg)

## Planned schedule

The table below is the intended serial schedule, not a claim that the timers
are currently enabled. The 2026-10-31 audit found all `homelab-backup-*` timers
disabled/inactive; see backlog items B2, B4, B5 and B8 before re-enabling any
class. Do not enable the GitLab class while the operator's size-based deferral
is in effect. The installed `homelab-backup-database-instances.timer` also
targets a wrapper whose current accepted arguments are only
`databases|gitlab|rustfs|retention`, while `schedule.yaml` does not list that
class; reconcile the unit, wrapper and schedule source as one reviewed change
before enabling it.

Jobs run serially behind one global lock:

| Local time | Job | Service interruption |
|---|---|---|
| 01:00 | PostgreSQL + CouchDB | None |
| 03:00 | Additional PostgreSQL instances | None |
| 04:00 | RustFS object export | None |
| 05:00 | GitLab native backup | None |
| 10:00 | Verify repositories and apply retention | None |
| 12:00 | Read-only health check | None |
| 13:00 | Host configurations | None |

If a prior job is still running, a VM100 scheduled class waits up to one hour
for the shared lock and then reports a missed window; it must not overlap
production backup work. Direct Pi executor calls fail fast by design.

The executable flow is defined in `automation/backup-runner/`:

- `run-class.sh` performs one class in export, upload, check, and Mezon
  post-check order;
- `run-retention.sh` owns the Pi repository maintenance lock; VM100 separately
  verifies the additional-instance and config repositories;
- `health-report.py` emits a secret-free status summary for Semaphore and
  alerting;
- `schedule.yaml` is the single schedule source. Do not add a second cron or
  systemd schedule while importing these jobs into Semaphore.

The current deployment record is [Backup Scheduler Re-enable](../deployments/backup-scheduler-2026-10-06.md),
and the point-in-time result is in the [runtime inventory](../deployments/runtime-inventory-2026-10-13.md).
VM100 timers are the intended schedule owner, but they are currently inactive;
do not restore the legacy Pi5 cron entry or enable GitLab implicitly while
repairing the scheduler.

## Google Drive and Retention

Use five encrypted restic repositories via a dedicated rclone Google Drive
remote pinned to the `Homelab Backup` folder. The populated repositories are
under the existing `homelab-backups/` child, so the configured `DRIVE_ROOT` is
`homelab-backups`:

```text
homelab-backups/databases
homelab-backups/database-instances
homelab-backups/gitlab
homelab-backups/rustfs
homelab-backups/configs
```

Retention policy:

- 14 daily snapshots;
- 8 weekly snapshots;
- 12 monthly snapshots.

The retention job runs `restic check` first and prunes only the matching
repository after a successful upload. It must not use `rclone sync --delete`,
Drive-wide age deletion, or a path outside the five repositories below the
pinned `Homelab Backup/homelab-backups` root.

After all required repository checks pass, the same retention window keeps the two
newest completed local staging runs per class on the export host. It never
removes an `.incomplete` run automatically.

The daily VM100 health check is read-only. It checks failed backup units, stale
markers, old incomplete runs, lock state, and free space, and reports detected
problems to Mezon without deleting backup data.

The rclone remote must be configured so deletion behavior is intentional. A
disposable backup folder is used to verify whether expired objects are trashed
or permanently removed before enabling production pruning.

## Mezon Status Reporting

The post-check script is:

```text
backup/scripts/post-check-report.sh
```

It calls:

```text
backup/scripts/notify-mezon.sh
```

The webhook URL is a secret and must be supplied through
`MEZON_WEBHOOK_URL_FILE=/run/secrets/mezon_backup_webhook`. Never commit or
print the URL. The payload is a Mezon channel webhook envelope with a plain-text
status message. One notification is sent after each verified class; a failed
post-check produces a failure notification and a non-zero exit code.

Local dry-run:

```bash
backup/scripts/post-check-report.sh \
  --kind databases \
  --run-dir /path/to/run \
  --summary 'database backup verified' \
  --dry-run
```

## CouchDB Native-Pull Staging

The CouchDB native-pull path is staged, not the production scheduled path.
Pi5 currently remains the export source for the `databases` class. The live
GET-only proxy is private LAN traffic:

```text
VM100 -> 10.10.0.5:15984 -> Pi5 couchdb-backup-proxy:8080 -> couchdb:5984
```

- The listener is not exposed through Traefik, Rathole or a public domain.
- Only VM100 (`10.10.0.31/32`) is allowed.
- Only `GET`/`HEAD` backup paths and the configured database allow-list are
  accepted; mutating requests are rejected.
- VM100 stores only `BACKUP_PROXY_TOKEN`; CouchDB admin credentials remain on
  Pi5. Deployment evidence and rollback are in
  [the proxy deployment note](../deployments/couchdb-backup-proxy-2026-10-21.md).

Verify from VM100 with the pinned curl image and the secret file, without
printing the token:

```bash
docker run --rm --network homelab-net \
  --env-file /etc/homelab-backup/secrets/couchdb-backup-proxy.env \
  curlimages/curl@sha256:d9b4541e214bcd85196d6e92e2753ac6d0ea699f0af5741f8c6cccbfcf00ef4b \
  sh -c 'curl -fsS -o /dev/null -w "%{http_code} %{size_download}\\n" \
    -H "Authorization: Bearer $BACKUP_PROXY_TOKEN" \
    http://10.10.0.5:15984/obsidian_vault'
```

Expected: non-empty `200` with the valid token and `401` with a wrong token.
Do not enable `BACKUP_COUCHDB_TRANSPORT=network-proxy` in the scheduled class
until a complete export, manifest comparison and isolated restore pass. The
rollback is to stop `couchdb-backup-proxy` on Pi5; the current Pi5 backup path
continues independently.

## Restore Order

1. Restore PostgreSQL globals/roles, then the selected database into an isolated
   target.
2. Restore CouchDB system/security metadata and selected documents.
3. Restore RustFS bucket settings/IAM metadata and selected objects.
4. Restore the selected configs snapshot into a scratch directory and compare
   checksums before considering any live replacement.
5. Restore GitLab on the exact source version and edition, then apply the
   configuration/secrets artifact.
6. Run representative application checks before any production cutover.

Production overwrite requires a separate approval. Monthly isolated restore
tests are mandatory before claiming operational recovery.

## Current Limitations

- The adapters have been exercised against current Pi5/VM100 data and isolated
  restore targets. Current restore evidence covers the latest database,
  database-instance, GitLab and RustFS snapshots; see the dated acceptance
  reports in `docs/deployments/` and the [rehearsal evidence](../deployments/backup-restore-rehearsal-2026-10-05.md).
- Semaphore and the internal provisioner are an active private provisioning
  control plane on Pi5. They are intentionally separate from the VM100 backup
  scheduler. Task 57 is the current read-only health acceptance; it does not
  replace remote restore testing.
- The Mezon webhook secret is intentionally not stored in this repository.
- Redis recovery is outside the generic database class. The Pi5 RDB/AOF
  service procedure passed a scratch restore on 2026-10-31; recurring Redis
  enrollment remains a separate operational decision.
- The `configs` class stores selected host configuration and secret-bearing
  files in its own encrypted Restic repository. Restore drills mirror the
  repository with rclone before restoring locally; this avoids making a large
  restore depend on a long-lived rclone stdio session.
- A successful database backup does not restore application files or RustFS
  objects; those are covered by their separate native restore drills.
- GitLab recovery requires PostgreSQL globals, the exact GitLab version and
  edition, the config/secrets artifact, and a compatible PostgreSQL major. The
  current dump is from PostgreSQL 16.14 using a PostgreSQL 17.10 client; a
  PostgreSQL 16 target needs the `transaction_timeout` compatibility handling
  documented in the GitLab backup README.
