---
type: Runbook
title: "Homelab Backup and Restore Runbook"
description: "Current backup paths, coverage gaps, restic runner procedures and restore order"
timestamp: 2026-10-31T00:00:00+07:00
---

# Homelab backup and restore runbook

**Owner:** Homelab operator · **Timezone:** `Asia/Ho_Chi_Minh`

## Current state (2026-10-31)

Three overlapping mechanisms exist. Only the first two run on a schedule.

| Path | Runs on | Covers | Schedule | Restore proof |
|---|---|---|---|---|
| **Databasus** (`db-management_databasus`) | VM110 `db-ops`; verification agent `pi-verifier-1` on Pi5 | 15 PostgreSQL jobs on the shared Pi5 cluster → Drive `Homelab Backup/databasus_backups` | Per-job, in Databasus | Automatic `After backup` restore verified for `n8n`, `homelab`, `relayhub`, `netbird`, `netbird_activity`, `netbird_idp`; other jobs dump/upload only |
| **db-management worker** (`db-management_worker`) | VM110 | Pi5 PostgreSQL, CouchLoom PostgreSQL, CouchDB DBs (via VM100 relays `10.10.0.31:15432/15433/15984`) → Drive, `gdrive://` receipts | `DB_MANAGEMENT_BACKUP_SCHEDULE_ENABLED=true` in source (live cadence unverified) | Receipts only |
| **Restic backup runner** (`homelab-ops/automation/backup-runner/`) | VM100 orchestrator, Pi5 executor | Classes `databases`, `database-instances`, `rustfs`, `gitlab`, `configs` → encrypted restic repos on Drive | **None.** No `homelab-backup-*` timers exist on VM100; run manually | `databases` restored 2026-10-31 ([evidence](../deployments/backup-repair-2026-10-31.md)) |

Coverage gaps: **GitLab, RustFS, Redis and host configs have no scheduled
backup.** GitLab is deliberately skipped (native backup grows to ~14 GB).
No VM image backup and no off-host target outside Proxmox. Cluster roles/grants
need `pg_dumpall --globals-only`, which only the restic `databases` class takes.
Reopened backlog items B2, B4, B5, B8 track re-enabling the schedule; the
consolidation design is in the
[IaC rebuild plan](../superpowers/plans/2026-10-31-lab-iac-automation-rebuild.md).
Databasus procedures: [Databasus operations](databasus-backup-operations.md).

## Operating principles

- Use the application's native CLI/API; back up online.
- Never `rsync` a live database or RustFS volume. A cold RustFS copy needs
  explicit approval, stopped writes, and an isolated restore check.
- A class is successful only after local validation, a readable remote
  snapshot, and manifest/checksum validation. A failed class never triggers
  retention deletion.
- A healthy container or HTTP 200 is not backup evidence.

## Restic runner classes

| Class | Content | Notes |
|---|---|---|
| `databases` | Pi5 PostgreSQL `pg_dump -Fc` per DB + `pg_dumpall --globals-only`; CouchDB export with security metadata | Exports from Pi5. Retired catalog entries are listed as excluded. |
| `database-instances` | Extra PostgreSQL instances on VM100 (CouchLoom, PG 17) | The old timer pointed at a wrapper that only accepts `databases|gitlab|rustfs|retention`; reconcile unit, wrapper and `schedule.yaml` before scheduling. |
| `rustfs` | Approved buckets via `rc`/S3 API with keys, sizes, ETags, metadata | Never copy `/data`. |
| `gitlab` | `gitlab-backup create` inside the Omnibus container + config/secrets + local Registry | Must record exact version/edition; Redis DB 2 excluded (rebuildable). Currently skipped. |
| `configs` | Pi5 edge/stack config (Traefik, AdGuard, Rathole, Compose/env) + VM100 app declarations | Fail-closed inventories; Pi exporter uses `alpine:3.22 --network none`; staging 0700, files 0600. |

Redis has a separate RDB/AOF procedure (snapshot + scratch `PING`/`DBSIZE`
check); NATS is not backed up.

Runner files: `run-class.sh` (export → upload → check → Mezon post-check),
`run-retention.sh`, `run-restore-drill.sh`, `schedule.yaml` (the single
schedule source — never add a second cron/timer), `pi-executor.sh`. Scheduled
classes share one global lock; a waiting VM100 job gives up after one hour and
reports a missed window. Do not restore the legacy Pi5
`/ssd-data/backup/simple-backup.sh` cron.

Intended serial schedule when re-enabled (not active): 01:00 databases,
03:00 database-instances, 04:00 rustfs, 05:00 gitlab, 10:00 verify +
retention, 12:00 health, 13:00 configs.

## Drive repositories and retention

Pi5 `/ssd-data/infra/backup/secrets/rclone.conf` and VM100
`/etc/homelab-backup/secrets/rclone.conf` point at the `Homelab Backup`
folder with `DRIVE_ROOT=homelab-backups`:

```text
homelab-backups/{databases,database-instances,gitlab,rustfs,configs}
```

Only `homelab-backups/databases` was re-initialized on 2026-10-31 (latest
snapshot `b1391e30…`); the others need a fresh run before they are trusted
(unverified). Retention: 14 daily, 8 weekly, 12 monthly; `restic check` before
prune; never `rclone sync --delete` or Drive-wide deletion. Locally the newest
two completed runs per class are kept; `.incomplete` runs are never auto-removed.

## Mezon reporting

`backup/scripts/post-check-report.sh` calls `notify-mezon.sh` after each class;
the webhook comes from `MEZON_WEBHOOK_URL_FILE=/run/secrets/mezon_backup_webhook`
(VM100: `/etc/homelab-backup/secrets/mezon-webhook`). Never print the URL.

```bash
backup/scripts/post-check-report.sh --kind databases --run-dir /path/to/run \
  --summary 'database backup verified' --dry-run
```

## CouchDB backup proxy

```text
VM100 / VM110 relay -> 10.10.0.5:15984 -> Pi5 couchdb-backup-proxy:8080 -> couchdb:5984
```

GET/HEAD only, database allow-list, VM100 source only, no public route. VM100
holds only `BACKUP_PROXY_TOKEN` (`/etc/homelab-backup/secrets/couchdb-backup-proxy.env`).
Verify without printing the token:

```bash
docker run --rm --network homelab-net \
  --env-file /etc/homelab-backup/secrets/couchdb-backup-proxy.env \
  curlimages/curl@sha256:d9b4541e214bcd85196d6e92e2753ac6d0ea699f0af5741f8c6cccbfcf00ef4b \
  sh -c 'curl -fsS -o /dev/null -w "%{http_code} %{size_download}\\n" \
    -H "Authorization: Bearer $BACKUP_PROXY_TOKEN" http://10.10.0.5:15984/obsidian_vault'
```

Expect non-empty `200`, and `401` with a wrong token. Rollback: stop
`couchdb-backup-proxy` on Pi5. The restic `databases` class still exports
CouchDB from Pi5 directly; do not set `BACKUP_COUCHDB_TRANSPORT=network-proxy`
there without a full export + restore comparison.

## Restore order

1. PostgreSQL globals/roles, then the selected DB into an isolated target
   (`pgvector/pgvector:pg16` for Pi5 data; PG 17 for CouchLoom).
2. CouchDB security metadata and documents (check document count).
3. RustFS bucket settings/IAM, then objects (verify checksums).
4. Configs snapshot into scratch; compare checksums before any live swap.
5. GitLab on the exact version/edition, then config/secrets. Dumps taken with a
   PG 17 client need `transaction_timeout` handling on a PG 16 target.
6. Application checks before any cutover. Production overwrite needs separate
   approval. Mirror a restic repo locally with rclone before a large restore.
