# Backup and Restore Rehearsal

**Date:** 2026-10-05
**Status:** Local artifacts and isolated restore tests verified; encrypted
Google Drive class uploads and scheduled runner are still pending.

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
cannot collide with backup metadata. The current code fix needs one fresh
RustFS export/restore run before the remote RustFS snapshot is accepted.

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

## Remaining gates

- Unlock the local 1Password SSH agent, copy the corrected restic runner to
  Pi5, and complete one verified snapshot in each of the three dedicated Drive
  repositories.
- Run the real post-check and sanitized Mezon notification for each class.
- Verify retention only after repository checks pass.
- Move the runner and durable Semaphore control metadata to VM100, create the
  no-op/backup/restore templates, then enable the serial schedule.
