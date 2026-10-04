# Homelab Backup Automation

This directory contains the backup policy, engine-specific automation, and
post-check notification contract. The backup system is **not deployed yet**;
the implementation plan is [here](../docs/superpowers/plans/2026-10-04-homelab-backup-control-plane.md).

## Rules

1. Prefer the application's native CLI or API.
2. Do not stop production services for scheduled backups.
3. Every completed backup must produce a manifest, a completion marker, and a
   remote snapshot ID.
4. Run `scripts/post-check-report.sh` only after the backup and remote upload
   verification succeed.
5. Report one status to Mezon after each backup class: PostgreSQL/CouchDB,
   GitLab, and RustFS.
6. Never store the Mezon webhook URL in Git. Provide it at runtime through
   `MEZON_WEBHOOK_URL_FILE` or a secret-mounted `MEZON_WEBHOOK_URL`.

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

- `manifest.json` with `status`, `kind`, `coverage`, and
  `remote_snapshot_id`;
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

For local validation without sending a message, add `--dry-run`.

## Status contract

The operator receives one message only after each class passes its post-check:

- `[HOMELAB BACKUP] [OK] databases: ...`
- `[HOMELAB BACKUP] [OK] gitlab: ...`
- `[HOMELAB BACKUP] [OK] rustfs: ...`
- `[HOMELAB BACKUP] [FAIL] <kind>: post-check failed ...`

The message must contain no passwords, OAuth tokens, webhook URLs, database
connection strings, or raw backup contents.
