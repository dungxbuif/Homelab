# Backup and Restore Rehearsal

**Date:** 2026-10-05
**Status:** Local exports, encrypted Google Drive uploads, retention checks,
Mezon post-checks, and remote restore rehearsals verified. The durable
Semaphore scheduler and UI-driven auto-enrollment remain pending.

## Evidence

### Databases on Pi5

Run `db-20261005-0100` completed online at:

```text
/ssd-data/infra/backups/homelab/db-20261005-0100
```

It contains `manifest.json`, `checksums.sha256`, `COMPLETE`, PostgreSQL
custom-format dumps plus globals, and paginated CouchDB NDJSON exports. The
run covered 14 PostgreSQL databases and 5 CouchDB databases, including the
large `homelab` CouchDB database without loading the whole export into Python
memory. The local checksum pass and post-check dry-run passed.

Restore rehearsals:

- PostgreSQL `bds_prod` restored into an isolated `bds_restore_20261005` and
  passed `SELECT 1`; the disposable database was removed.
- CouchDB `obsidian_vault` restored into `obsidian_restore_20261005` with
  45,993 documents; the disposable database was removed.

This first local run predates the lifecycle filter and includes the two
catalog entries already marked `retired`. It is retained as historical
evidence only; the final production run must be regenerated so its manifest
records those exclusions instead of treating retired services as live data.

### RustFS on Pi5

Run `rustfs-20261005-0100-full` completed through the S3 API at:

```text
/ssd-data/infra/backups/homelab/rustfs-20261005-0100-full
```

All 8 approved buckets were exported, checksummed, and marked complete.
`whiteboard` restored into an isolated bucket with zero production objects,
then the test bucket was removed. The rehearsal found and fixed a verifier
bug that would have copied backup control files into the target bucket;
regression coverage now isolates all object payloads under `objects/`, so a
legitimate production object named `manifest.json` or `bucket-metadata.json`
cannot collide with backup metadata. The final RustFS export and remote
restore below provide the acceptance evidence for that fix.

### GitLab on VM100

The final v4 run was created online from GitLab CE `18.11.11` and staged on
Pi5 as:

```text
/ssd-data/infra/backups/homelab/gitlab-20261005-0100-final
```

Native archive, config/secrets archive, local Registry archive, manifest,
checksums, and `COMPLETE` were verified. The native SQL was restored after
loading PostgreSQL globals into an isolated PostgreSQL 17.10 container. The
restored DB contained 1,026 public tables, 1 project, and 3 users; the
temporary container was removed. The manifest records source PostgreSQL
16.14 and dump client 17.10.

### Restic tooling

A disposable Drive repository smoke test completed successfully, including
init, backup, repository check, restore, content comparison, and cleanup.
The first real upload attempt exposed that a read-only rclone config cannot
refresh an OAuth token. `restic-lib.sh` now copies the config into a writable
per-process working directory while preserving the source config.

### Final Drive window

The corrected runner completed one real snapshot in each dedicated repository:

| Class | Run | Result |
|---|---|---|
| Databases | `db-20261005-140503-final` | PostgreSQL 12 databases plus globals and CouchDB 5 databases; snapshot/check passed |
| RustFS | `rustfs-20261005-140503-final` | 7 active buckets; retired `goclaw` excluded; snapshot/check passed |
| GitLab | `gitlab-20261005-0100-final` | GitLab CE `18.11.11` native archive/config/registry artifacts; snapshot/check passed |

The three repositories are isolated below `homelab-backups/databases`,
`homelab-backups/rustfs`, and `homelab-backups/gitlab`. Retention passed
pre-check and post-prune repository checks for all three classes. The legacy
Pi cron entry calling `/ssd-data/backup/simple-backup.sh all` was disabled; the
script and historical artifacts were retained for audit.

Remote restore evidence:

- The database snapshot restored 6.5 GiB to staging, passed all checksums, and
  restored `bds_prod` into an isolated PostgreSQL database with `SELECT 1`.
- The RustFS snapshot restored 754 MiB to staging, passed all checksums, and
  restored the `obsidian` bucket into an isolated bucket with 2,485 objects
  matching the manifest.
- The GitLab snapshot restored 5.4 MiB to staging, passed all checksums,
  `tar -tf`, and `gzip -t` validation.

Each class received a success post-check through the configured Mezon webhook.
No production database, bucket, or service was stopped. Disposable restore
databases, buckets, and staging directories were removed after verification.

## Remaining gates

- Deploy the durable runner and Semaphore control metadata on the approved
  host, with one scheduler owner and no replacement cron.
- Implement the UI-driven provisioning workflow: create DB/user or bucket,
  smoke-test it, atomically register the catalog entry, and let the next
  backup discover it automatically.
- Add the nightly live-resource/catalog drift audit and Mezon alert.
