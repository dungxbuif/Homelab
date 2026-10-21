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
BACKUP_COUCHDB_TRANSPORT=network-proxy
BACKUP_COUCHDB_NETWORK=homelab-net
BACKUP_COUCHDB_CLIENT_IMAGE=curlimages/curl@sha256:<approved-digest>
BACKUP_COUCHDB_CREDENTIALS_FILE=/etc/homelab-backup/secrets/couchdb-backup-proxy.env
BACKUP_COUCHDB_ENDPOINT=http://10.10.0.5:15984
BACKUP_COUCHDB_COMPRESSION=gzip
```

The proxy credentials file contains only `BACKUP_PROXY_TOKEN`; CouchDB admin
credentials remain on Pi5.

On VM100, the proxy file is root-owned and readable only by the backup runtime
group (`0640`); on Pi5, the token source remains root-owned and private. Neither
file is committed. The proxy is deployed and verified on the private LAN, but
the scheduled `databases` class still uses the existing Pi5 transport until the
comparison and restore gate below is accepted.
The PostgreSQL globals export also uses the private network path with
`backup_ro`; it is always requested with `--no-role-passwords`, so role password
hashes are not written into the backup payload. The per-database dumps use the
private `postgres-pg:5432` endpoint directly; PgBouncer remains an application
pooler and is not a backup dependency. Do not enable this mode until the
dedicated identities, image digests and one-week manifest/restore comparison
are reviewed. Removing Pi5 Restic/Drive secrets is a later acceptance step,
not an automatic consequence of setting these variables.

### Live CouchDB proxy checks

The Pi5 proxy listens only on the private LAN address `10.10.0.5:15984`; it is
not routed through Traefik, Rathole or a public domain. It is restricted to the
VM100 source address and the allow-listed backup databases/paths. The upstream
connection stays inside Pi5's Docker network at `couchdb:5984`.

The exporter requests `_all_docs` in 3,000-document pages and rejects any
single response larger than 128 MiB. This keeps attachment-heavy exports
practical without allowing an unexpectedly large response to consume
unbounded memory. `BACKUP_COUCHDB_COMPRESSION=gzip` stores document streams as
`.docs.ndjson.gz`; it is optional and defaults to uncompressed `.ndjson` for
backward compatibility. The native restore helper reads either form. For a
VM100 staging experiment, set `BACKUP_COUCHDB_MIN_FREE_BYTES` to a safety
floor; the exporter checks it before each page and fails closed. It is unset
by default. The experimental `backup/scripts/stream-couchdb.py` source
boundary emits one database as gzip NDJSON to stdout for a future Restic
`--stdin` integration; it is not part of the scheduled runner yet.

Run this check from VM100 without printing the token:

```bash
docker run --rm --network homelab-net \
  --env-file /etc/homelab-backup/secrets/couchdb-backup-proxy.env \
  curlimages/curl@sha256:d9b4541e214bcd85196d6e92e2753ac6d0ea699f0af5741f8c6cccbfcf00ef4b \
  sh -c 'curl -fsS -o /dev/null -w "%{http_code} %{size_download}\\n" \
    -H "Authorization: Bearer $BACKUP_PROXY_TOKEN" \
    http://10.10.0.5:15984/obsidian_vault'
```

Expected results are a non-empty `200` response with the valid token and
`401` with an intentionally incorrect token. A complete staged export and
isolated restore of `obsidian_vault` matched `49,210` documents. The full
inventory probe was stopped while exporting the large `homelab` database at
about 83% VM100 disk usage; it did not modify CouchDB or the production backup
marker.

To roll back the staged proxy without touching CouchDB:

```bash
cd /ssd-data/infra
docker compose -f docker-compose.yml \
  -f couchdb/backup-proxy.compose.yml stop couchdb-backup-proxy
```

The scheduled backup remains on the Pi5 path during this staged period, so
stopping the proxy does not disable the current production backup.

## Status contract

The operator receives one message only after each class passes its post-check:

- Success notifications are short and human-readable, for example
  `✅ Backup thành công: PostgreSQL + CouchDB` followed by a confirmation
  that the backup was saved and verified.
- Failure and warning notifications add only the relevant reason and readable
  disk sizes; run IDs are retained for troubleshooting.
- `[HOMELAB BACKUP] [FAIL] <kind>: post-check failed ...`

The message must contain no passwords, OAuth tokens, webhook URLs, database
connection strings, or raw backup contents.
