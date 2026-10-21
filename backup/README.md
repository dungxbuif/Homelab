# Homelab Backup Automation

This directory contains the backup policy, engine-specific automation, and
post-check notification contract. Local and remote restore rehearsals are
verified; the current evidence is recorded in
[`docs/deployments/backup-restore-rehearsal-2026-10-05.md`](../docs/deployments/backup-restore-rehearsal-2026-10-05.md).
The private Semaphore UI and internal provisioner are still a pilot. The
production backup timers are enabled on VM100, with the first end-to-end
scheduled window pending. Semaphore is the operator surface; it
does not receive Docker credentials or execute arbitrary shell commands. The
provisioner is the narrow internal boundary that owns Docker API access. The
implementation plan is [here](../docs/superpowers/plans/2026-10-04-homelab-backup-control-plane.md).

## Rules

1. Prefer the application's native CLI or API.
2. Do not stop production services for scheduled backups.
3. Every completed backup must produce an immutable manifest, a completion
   marker, and a local `remote/snapshot-id` after the remote snapshot is
   verified.
4. Run `scripts/post-check-report.sh` only after the backup and remote upload
   verification succeed.
5. Report one status to Mezon after each backup class: shared PostgreSQL/CouchDB,
   additional PostgreSQL instances, GitLab, and RustFS.
6. Never store the Mezon webhook URL in Git. Provide it at runtime through
   `MEZON_WEBHOOK_URL_FILE` or a secret-mounted `MEZON_WEBHOOK_URL`.

## Provisioning boundary

New databases are provisioned as an application unit: a dedicated database,
one least-privilege application owner/user, a backup policy reference, and a
catalog entry containing only secret references. The provisioning request is
declarative and validated; it cannot submit arbitrary SQL. The backup runner
uses its own backup credential and never reuses the application password.

PostgreSQL roles do not receive `SUPERUSER`, `CREATEDB`, or `CREATEROLE`.
CouchDB uses a per-database security policy and a named member/role. Redis is
not provisioned or backed up by this control plane.

Inventory entries marked `retired` remain in the catalog for audit history but
are excluded from new exports. Each adapter records the excluded names in its
manifest so a smaller current backup cannot be mistaken for missing coverage.

The private Semaphore provisioning workflow registers a newly created database
in this catalog only after its native create and smoke test pass. Semaphore
calls the internal `homelab-provisioner` service; the UI has no Docker socket.
The next scheduled runner then includes the database automatically; backup
scripts do not need per-application edits. RustFS bucket provisioning is still
an explicit follow-up and is not silently implied by database provisioning.

## Native mechanism matrix

| Backup class | Required mechanism | Not used as the scheduled mechanism |
|---|---|---|
| PostgreSQL | `pg_dump`, `pg_dumpall --globals-only` | live data-directory copy |
| Additional PostgreSQL instances | native `pg_dump` on the owning host | cross-host volume copy or Pi-side container guessing |
| CouchDB | CouchDB replication/HTTP API or verified native admin tooling | live volume copy |
| GitLab | `gitlab-backup create` and supported config/secrets backup | custom repository `rsync` |
| RustFS | `rc`/S3 API object export or replication | live-volume `rsync` |
| Redis | excluded by policy | all snapshots |
| NATS | not a database; excluded | all snapshots |

GitLab's native backup may use `rsync` internally as an implementation
dependency. That does not authorize a separate live-volume rsync job.

## Post-check and notification

Each engine job writes a run directory with:

- `manifest.json` with `status`, `kind`, and `coverage`; the upload step keeps
  it immutable and records the repository-specific ID in `remote/snapshot-id`
  plus the scheduler ID in `remote/run-id`;
- `checksums.sha256`;
- `COMPLETE` marker created only after upload and repository verification.

Then run:

```bash
MEZON_WEBHOOK_URL_FILE=/run/secrets/mezon_backup_webhook \
  ./scripts/post-check-report.sh \
  --kind databases \
  --run-dir /var/lib/homelab-backup/runs/<run-id> \
  --summary 'PostgreSQL and CouchDB backup verified' \
  --run-id <run-id> \
  --snapshot-id <restic-snapshot-id>
```

The reporter verifies the manifest, completion marker, checksums, coverage,
and snapshot ID before sending a success message. Any failed check sends a
failure message and exits non-zero. The Mezon payload uses the documented
`{"type":"hook","message":{"t":"..."}}` envelope.

`upload-restic.sh` accepts an optional explicit run ID. The backup runner uses
it so GitLab's nested `complete/` directory cannot become the repository tag.

For local validation without sending a message, add `--dry-run`.

## Current runner state

- Pi5 staging path: `/ssd-data/infra/backups/homelab`.
- VM100 is the target for the durable runner and control metadata; the current
  Semaphore/provisioner pair is a private provisioning pilot on Pi5.
- Restic repositories are isolated below the existing `homelab-backups/`
  child of the pinned Google Drive folder: the runtime uses
  `DRIVE_ROOT=homelab-backups` and the effective paths are
  `homelab-backups/databases`, `homelab-backups/database-instances`,
  `homelab-backups/rustfs`, and `homelab-backups/gitlab` on `homelab1`.
- `restic-lib.sh` uses a writable per-process copy of `rclone.conf`, so OAuth
  refreshes do not modify the source config or fail on a read-only mount. The
  runner refuses to implicitly initialize a repository after a failed
  preflight; `RESTIC_ALLOW_INIT=true` is required for a controlled first setup.
  The Drive transport defaults to 64 MiB chunks, one initial request per
  pacing window, and bounded retries to avoid turning Google Drive rate limits
  into an unbounded or silent backup failure.
- The production Drive OAuth client belongs to Google Cloud project
  `homelab-backup-488616`. Runtime configs on Pi5 and VM100 retain the pinned
  `Homelab Backup` folder and the existing `homelab-backups/` repositories;
  client secrets and tokens remain host-local and are never committed.
- No production service is stopped by the online backup wrappers.

## Optional VM100 native pull transport

The default adapter transport remains the Pi5 container path. During the B9
comparison window, VM100 may opt into private-network exports by setting these
runtime-only values in `/etc/homelab-backup/runner.env`:

```text
BACKUP_POSTGRES_TRANSPORT=network
BACKUP_POSTGRES_NETWORK=pg-net
BACKUP_POSTGRES_CLIENT_IMAGE=postgres@sha256:<approved-digest>
BACKUP_POSTGRES_CREDENTIALS_FILE=/etc/homelab-backup/secrets/postgres-backup.env
BACKUP_POSTGRES_HOST=postgres-pg
BACKUP_POSTGRES_PORT=5432
BACKUP_POSTGRES_USER=backup_ro
BACKUP_POSTGRES_GLOBALS_TRANSPORT=network
BACKUP_POSTGRES_GLOBALS_USER=backup_ro
BACKUP_COUCHDB_TRANSPORT=network
BACKUP_COUCHDB_NETWORK=homelab-net
BACKUP_COUCHDB_CLIENT_IMAGE=curlimages/curl@sha256:<approved-digest>
BACKUP_COUCHDB_CREDENTIALS_FILE=/etc/homelab-backup/secrets/couchdb-backup.env
BACKUP_COUCHDB_ENDPOINT=http://couchdb:5984
```

The files contain only runtime credentials and remain root-owned, mode `0600`.
The PostgreSQL globals export also uses the private network path with
`backup_ro`; it is always requested with `--no-role-passwords`, so role password
hashes are not written into the backup payload. The per-database dumps use the
private `postgres-pg:5432` endpoint directly; PgBouncer remains an application
pooler and is not a backup dependency. Do not enable this mode until the
dedicated identities, image digests and one-week manifest/restore comparison
are reviewed. Removing Pi5 Restic/Drive secrets is a later acceptance step,
not an automatic consequence of setting these variables.

## Status contract

The operator receives one message only after each class passes its post-check:

- `[HOMELAB BACKUP] [OK] databases: ...`
- `[HOMELAB BACKUP] [OK] database-instances: ...`
- `[HOMELAB BACKUP] [OK] gitlab: ...`
- `[HOMELAB BACKUP] [OK] rustfs: ...`
- `[HOMELAB BACKUP] [FAIL] <kind>: post-check failed ...`

The message must contain no passwords, OAuth tokens, webhook URLs, database
connection strings, or raw backup contents.
