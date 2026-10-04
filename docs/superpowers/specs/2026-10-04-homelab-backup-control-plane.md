# Homelab Backup Control Plane Specification

**Date:** 2026-10-04  
**Status:** Proposed for implementation review  
**Scope:** Database provisioning UI, database backups, RustFS object backup, and GitLab application backup

## Goal

Provide one private operator workflow for creating and cataloging databases, running safe online backups, uploading encrypted backup history to Google Drive, and testing restores without stopping production services.

## Decisions

- Pi5 remains the datastore host. VM100 owns the automation runner and operator UI.
- PostgreSQL and CouchDB are included in the generic database backup job.
- Redis is explicitly excluded from backup. NATS is not a database and is excluded.
- GitLab uses its native `gitlab-backup create` workflow as a separate application backup. Its required configuration and secrets are handled by that GitLab-specific workflow, not by the generic database job.
- RustFS uses S3/API-level object backup while running. A stopped-volume `rsync` copy is allowed only as an emergency cold snapshot and is not the scheduled mechanism.
- No scheduled job stops PostgreSQL, CouchDB, RustFS, GitLab, or other production services.
- Google Drive is reached through an encrypted restic repository using rclone as transport. The jobs never use `rclone sync --delete` against production data or the whole Drive.
- Backup content is isolated into three dedicated Drive repositories/prefixes: `databases`, `rustfs`, and `gitlab`.
- Default retention is 14 daily, 8 weekly, and 12 monthly snapshots. Prune runs only after a successful upload and repository check.
- Access is private through LAN/NetBird. No public route is added for the control UI or backup runner.
- After each backup class completes its post-check, send exactly one sanitized status message to the configured Mezon channel webhook. The webhook URL is runtime secret material and is never committed or printed.

## Current Coverage

### Generic database job

- PostgreSQL databases documented on Pi5, including application databases and the `homelab` control database once verified.
- CouchDB document databases used by Obsidian sync.
- PostgreSQL globals, roles, grants, extensions, and per-database logical dumps.
- Redis snapshots are not produced.

### GitLab job

- GitLab CE Omnibus `gitlab_gitlab` on VM100.
- Native GitLab database, repositories, local uploads, artifacts, packages, LFS, and local registry data where supported by the current filesystem-backed configuration.
- GitLab configuration and secrets needed for restore, including `gitlab.rb` and `gitlab-secrets.json`.
- Redis DB 2 is not part of the GitLab backup; cache, sessions, and Sidekiq queues are expected to rebuild.
- Object-storage-backed GitLab data, if enabled later, must be added to the GitLab/RustFS coverage contract.

### RustFS job

- Buckets and objects through the S3-compatible API.
- Per-bucket manifest with bucket name, object key, size, checksum/ETag when available, version information when available, and export timestamp.
- Historical backup versions are supplied by restic snapshots, not by copying the live RustFS volume.
- RustFS IAM/config metadata required to recreate the bucket access model is tracked as a separate export artifact.

## Architecture

```text
Private operator UI (Semaphore + Ansible templates)
        |
        +--> DB provisioning jobs ------------> Pi5 PostgreSQL / CouchDB
        |
        +--> DB backup runner ----------------> Pi5 PostgreSQL / CouchDB
        |
        +--> GitLab backup job ---------------> VM100 GitLab native CLI
        |
        +--> RustFS backup job ---------------> Pi5 RustFS S3 API
        |
        +--> restic encrypted repositories --> rclone --> dedicated Google Drive folders
```

The operator UI is a private Semaphore installation. It provides parameterized provisioning, backup, restore-test, status, and audit history. Ansible owns the idempotent implementation; the UI does not execute arbitrary SQL or shell commands.

## Provisioning Contract

Every request contains:

- `engine`: `postgresql` or `couchdb`
- `name`: validated service/database name
- `application`: owning app
- `environment`: `prod`, `staging`, or `dev`
- `owner_role` or CouchDB security identity
- `backup_policy`: enabled schedule, retention class, and restore-test cadence
- `secret_ref`: reference to a generated secret, never the secret value

PostgreSQL provisioning creates the database, owner role, least-privilege grants, approved extensions, and catalog record. CouchDB provisioning creates the database, user/security policy, and catalog record. Redis provisioning is intentionally out of scope.

## Backup Contract

Each job:

1. Acquires one global lock and validates credentials, target reachability, free staging space, and Drive quota.
2. Creates a timestamped incomplete run directory on VM100.
3. Exports all required targets using the engine-specific adapter.
4. Writes a manifest and checksums, then atomically marks the run complete.
5. Creates a restic snapshot tagged with `class`, `engine`, `application`, and `database_or_bucket`.
6. Verifies the repository snapshot before any pruning.
7. Applies the class retention policy and removes only expired objects from the dedicated backup repository.
8. Emits a success/failure record visible in Semaphore and the operator log.
9. Sends one Mezon success message only after the post-check passes; sends a failure message and exits non-zero when any post-check fails.

Any required target failure fails the overall run. A partial run is never reported as a successful full backup.

## Schedule

All times use `Asia/Ho_Chi_Minh` and execute serially:

| Time | Job |
|---|---|
| 01:00 | PostgreSQL and CouchDB logical backups |
| 02:30 | GitLab native backup and configuration/secrets backup |
| 04:30 | RustFS bucket/object export |
| 05:30 | Restic verification and retention/prune |

If an earlier job is still running, later jobs wait on the global lock. A job that misses the window emits an alert instead of overlapping production backup work.

## Restore Contract

- Restore defaults to an isolated target, never production.
- PostgreSQL restores roles/globals first, then a selected database into a disposable database.
- CouchDB restores into a disposable database or isolated CouchDB instance and checks document counts and representative reads.
- GitLab restore uses the same GitLab version and CE/EE type as the backup, first in an isolated VM100 target.
- RustFS restore recreates bucket settings/IAM metadata, then restores selected objects and verifies checksums.
- Monthly restore rehearsal is required before declaring the system operational.

## Security and Data Handling

- Google Drive OAuth/rclone configuration and restic passwords are deployed as private secrets, never committed or printed.
- The backup runner has only the read/backup privileges required for each engine.
- Restore credentials are separate from backup credentials where the engine supports it.
- The UI is private and does not display database passwords or backup encryption keys.
- Retention deletion is scoped to the dedicated backup repositories. No broad Drive cleanup is allowed.

## Acceptance Criteria

- An operator can create a PostgreSQL database/user and a CouchDB database/security policy from the private UI without arbitrary SQL.
- PostgreSQL and CouchDB backups run while production services remain available.
- Redis and NATS do not produce backup artifacts.
- GitLab native backup completes online, includes current local GitLab data, and separately preserves required configuration/secrets.
- RustFS backup runs through the S3/API path; no live volume `rsync` is used.
- Three encrypted repositories are present in the dedicated Google Drive folder.
- Retention keeps 14 daily, 8 weekly, and 12 monthly snapshots and deletes only expired backup data after verification.
- A restore rehearsal succeeds for one PostgreSQL database, one CouchDB database, one RustFS bucket/object set, and a GitLab disposable target.
- Each completed class produces exactly one Mezon status message without secrets, tokens, connection strings, or raw backup contents.
