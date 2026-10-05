# Homelab Backup Automation

This directory contains the backup policy, engine-specific automation, and
post-check notification contract. The implementation and local restore
rehearsal are in progress; the current evidence is recorded in
[`docs/deployments/backup-restore-rehearsal-2026-10-05.md`](../docs/deployments/backup-restore-rehearsal-2026-10-05.md).
The private Semaphore UI is still a pilot and production schedules remain
disabled. The implementation plan is [here](../docs/superpowers/plans/2026-10-04-homelab-backup-control-plane.md).

## Rules

1. Prefer the application's native CLI or API.
2. Do not stop production services for scheduled backups.
3. Every completed backup must produce an immutable manifest, a completion
   marker, and a local `remote/snapshot-id` after the remote snapshot is
   verified.
4. Run `scripts/post-check-report.sh` only after the backup and remote upload
   verification succeed.
5. Report one status to Mezon after each backup class: PostgreSQL/CouchDB,
   GitLab, and RustFS.
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

## Native mechanism matrix

| Backup class | Required mechanism | Not used as the scheduled mechanism |
|---|---|---|
| PostgreSQL | `pg_dump`, `pg_dumpall --globals-only` | live data-directory copy |
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
  it immutable and records the repository-specific ID in `remote/snapshot-id`;
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
- VM100 is the target for the durable runner; the current Semaphore service is
  only a private UI pilot on Pi5.
- Restic repositories are isolated at `homelab-backups/databases`,
  `homelab-backups/rustfs`, and `homelab-backups/gitlab`.
- `restic-lib.sh` uses a writable per-process copy of `rclone.conf`, so OAuth
  refreshes do not modify the source config or fail on a read-only mount.
- No production service is stopped by the online backup wrappers.

## Status contract

The operator receives one message only after each class passes its post-check:

- `[HOMELAB BACKUP] [OK] databases: ...`
- `[HOMELAB BACKUP] [OK] gitlab: ...`
- `[HOMELAB BACKUP] [OK] rustfs: ...`
- `[HOMELAB BACKUP] [FAIL] <kind>: post-check failed ...`

The message must contain no passwords, OAuth tokens, webhook URLs, database
connection strings, or raw backup contents.
