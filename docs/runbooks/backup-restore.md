# Homelab Backup and Restore Runbook

**Status:** Online adapters and isolated restore rehearsal verified on 2026-10-05;
encrypted Drive upload and scheduled deployment remain pending
**Owner:** Homelab operator  
**Timezone:** `Asia/Ho_Chi_Minh`

## Scope

This runbook covers three independent backup classes:

1. PostgreSQL and CouchDB databases on Pi5.
2. GitLab CE application data on VM100.
3. RustFS buckets and objects on Pi5.

Redis and NATS are deliberately excluded. The generic database backup does not
include application files, Git repositories, uploads, artifacts, or object
storage. GitLab and RustFS have separate native/object-aware workflows because
their recoverable data is not database-only.

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
  passed explicitly to the post-check.
- A failed class never triggers retention deletion.

## Backup Classes

### PostgreSQL and CouchDB

The database runner executes native logical exports online:

- PostgreSQL: one `pg_dump` custom archive per database and one
  `pg_dumpall --globals-only` export for roles/grants/globals.
- CouchDB: online replication/HTTP export with system/security metadata recorded
  in the manifest.
- Redis is not queried or exported.

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
are expected to rebuild after restore.

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

## Schedule

Jobs run serially behind one global lock:

| Local time | Job | Service interruption |
|---|---|---|
| 01:00 | PostgreSQL + CouchDB | None |
| 02:30 | GitLab native backup + config/secrets | None |
| 04:30 | RustFS object export | None |
| 05:30 | Verify repositories and apply retention | None |

If a prior job is still running, the next job waits or reports a missed window;
it must not overlap production backup work.

The executable flow is defined in `automation/backup-runner/`:

- `run-class.sh` performs one class in export, upload, check, and Mezon
  post-check order;
- `run-retention.sh` owns the separate 05:30 repository maintenance lock;
- `health-report.py` emits a secret-free status summary for Semaphore and
  alerting;
- `schedule.yaml` is the single schedule source. Do not add a second cron or
  systemd schedule while importing these jobs into Semaphore.

## Google Drive and Retention

Use three encrypted restic repositories via a dedicated rclone Google Drive
remote:

```text
homelab-backups/databases
homelab-backups/gitlab
homelab-backups/rustfs
```

Retention policy:

- 14 daily snapshots;
- 8 weekly snapshots;
- 12 monthly snapshots.

The retention job runs `restic check` first and prunes only the matching
repository after a successful upload. It must not use `rclone sync --delete`,
Drive-wide age deletion, or a path outside `homelab-backups/`.

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

## Restore Order

1. Restore PostgreSQL globals/roles, then the selected database into an isolated
   target.
2. Restore CouchDB system/security metadata and selected documents.
3. Restore RustFS bucket settings/IAM metadata and selected objects.
4. Restore GitLab on the exact source version and edition, then apply the
   configuration/secrets artifact.
5. Run representative application checks before any production cutover.

Production overwrite requires a separate approval. Monthly isolated restore
tests are mandatory before claiming operational recovery.

## Current Limitations

- The adapters have been exercised against current Pi5/VM100 data and local
  restore targets, but the three real Drive snapshots and production post-check
  notifications are still pending. See the [rehearsal evidence](../deployments/backup-restore-rehearsal-2026-10-05.md).
- The Semaphore service is a private UI pilot on Pi5. The durable runner,
  provisioning templates, and scheduler still belong on VM100.
- The Mezon webhook secret is intentionally not stored in this repository.
- Redis recovery is out of scope.
- A successful database backup does not restore application files or RustFS
  objects.
- GitLab recovery requires PostgreSQL globals, the exact GitLab version and
  edition, the config/secrets artifact, and a compatible PostgreSQL major. The
  current dump is from PostgreSQL 16.14 using a PostgreSQL 17.10 client; a
  PostgreSQL 16 target needs the `transaction_timeout` compatibility handling
  documented in the GitLab backup README.
