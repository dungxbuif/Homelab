# Database Backups to Google Drive

Status: proposal, not deployed. Reviewed 2026-09-13. Current runtime inventory,
database sizes, Drive credentials, available quota and existing schedules still
need verification. This is backup with recovery history, not database replication
or a live filesystem mirror.

Existing state, clarified by the owner: a whole-directory upload to Google Drive
already exists. The requirement is to replace that workflow with database-aware
backups across multiple engines while keeping Pi5 dedicated to datastores. Do
not disable or delete the existing uploads until replacement backups and restores
have been verified. Existing cloud archives must be preserved during migration.

## Recommendation

Use database-native exports, restic for encrypted versioned backups, and rclone
as the Google Drive transport. Use the proposed Semaphore/Ansible installation
for scheduling, manual execution, status and controlled restore jobs. No new
public endpoint or database host port is required.

Run the main backup job in a container on VM100, connected only to the necessary
private datastore network. PostgreSQL remains on Pi5 and is reached through its
Docker service name, directly rather than through transaction pooling. Prefer
engine-native remote export mechanisms. Pi5-local filesystem access, if
unavoidable for an engine's consistent backup, is an implementation decision to
review explicitly, not permission to add a permanent backup stack to Pi5. Do not
mount the Docker socket into a general backup container by default.

```text
Pi5 production databases
  -> engine-specific consistent export
  -> completed staging files on VM100
  -> restic encrypted repository through rclone
  -> dedicated Google Drive backup folder

Semaphore/Ansible: schedule, monitor, verify, restore-test
```

Restic officially supports Google Drive through its rclone backend. It does not
need a mounted Drive filesystem or a public REST endpoint for this integration.
Backups are encrypted before reaching Drive; retain the repository password
outside the lab and outside this repository. Drive contains restic repository
objects, not directly browsable SQL files. Recovery uses restic first, then the
database restore tool. [Restic backend documentation](https://restic.readthedocs.io/en/stable/030_preparing_a_new_repo.html)

## Database Coverage

Keep an explicit inventory of approved database engines and instances. Each
engine adapter owns export, validation and restore; restic/rclone own only
storage and transport. Adding a new engine requires its native backup and restore
procedure, not simply adding its data directory to a sync list. Record success,
failure, last restorable backup and retention per instance so one healthy engine
cannot hide missing coverage elsewhere. The table below reflects documented
datastores, not a freshly verified exhaustive runtime inventory.

| Data | Consistent backup method | Important recovery dependency |
|---|---|---|
| PostgreSQL 16 | Separate `pg_dump` custom-format archive per approved database; `pg_dumpall --globals-only` for shared roles | Compatible server/client versions, extensions, roles, grants and configuration |
| Redis | Completed RDB snapshot; inspect whether data is disposable cache or persistent queue/state | Record persistence settings; do not blindly copy an actively changing multipart AOF |
| CouchDB | Documented database-file backup or controlled replication into a backup instance followed by historical snapshots | Include system databases and configuration/security metadata needed for recovery |
| Application secrets and assets | Encrypted backup of required configuration, keys and persistent uploads | DB backup alone may not recover encrypted credentials or referenced objects |

PostgreSQL dumps are consistent within each database, not one atomic snapshot
across every database and object store. If an app needs coordinated asset and DB
recovery, establish its write-quiescing or versioning procedure. `pg_dump` does
not contain cluster-wide roles, hence the separate globals export. Use a
restricted backup identity where possible; globals may require additional
privileges and must be protected as sensitive data. [pg_dump](https://www.postgresql.org/docs/16/app-pgdump.html), [pg_dumpall](https://www.postgresql.org/docs/16/app-pg-dumpall.html)

Redis documents safely copying completed RDB files and caveats around AOF backup.
CouchDB documents replication and append-only database-file backup. Its native
file procedure is an engine-specific exception, not permission to copy arbitrary
live database volumes. Continuous replication by itself is not historical
backup because destructive changes can propagate. [Redis persistence](https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/), [CouchDB backups](https://docs.couchdb.org/en/stable/maintenance/backups.html)

Inventory application encryption keys such as n8n's credential key, plus any
future NetBird/Semaphore key material. RustFS objects require a separate scoped
object-backup plan; an SQL dump does not include them. Do not claim all apps are
recoverable until database-to-assets-to-secrets coverage has been checked.

## Alternatives

| Option | Fit |
|---|---|
| **restic + rclone + Semaphore** | Recommended: encrypted history and retention with the automation interface already selected |
| Native DB dumps + rclone crypt copy | Simpler individual encrypted files, but retention, manifests and restore verification need more custom handling |
| Backrest + restic/rclone | Useful dedicated backup UI if browsing/restoring backups becomes a priority; adds another controller and still needs DB-aware export hooks |

Backrest provides a web UI, scheduling and hooks around restic. If adopted later,
give each repository a single scheduling owner instead of running competing
Semaphore and Backrest maintenance schedules. [Backrest project](https://github.com/garethgeorge/backrest), [rclone crypt](https://rclone.org/crypt/)

Do not use bidirectional sync or `rclone sync` on production database directories.
Do not promise that deduplication makes each fresh SQL dump a small incremental
database backup. Compression and data layout affect reuse; benchmark compressed
versus uncompressed custom dumps with restic compression before selecting the
default for larger databases.

## Initial Schedule and Retention

Proposed defaults, subject to measured DB size and Drive quota:

- Daily backup at 01:00 Asia/Ho_Chi_Minh; on-demand backup before risky migrations.
- Seven days of completed local exports on VM100 persistent storage, not `/tmp`.
- Remote retention: 14 daily, 8 weekly and 12 monthly snapshots.
- Weekly repository check with rotating data-read coverage; periodic full check
  when bandwidth permits.
- Monthly restore rehearsal in an isolated container on VM100.
- Alert on any failed export/upload, low disk/quota, or last successful offsite
  backup older than 26 hours. Log retention must also be finite.

Daily backups imply up to roughly 24 hours of data loss under a healthy schedule;
failures can increase that window. More frequent dumps are possible. Recovery to
arbitrary recent timestamps requires a separate PostgreSQL base-backup/WAL
archiving design, not just restic over daily dumps.

Retention must be implemented using restic's snapshot policies and `prune`, not
Drive file-age deletion. Use stable snapshot paths/tags/grouping so each dated
staging directory does not accidentally become a separate retention group.
Schedule prune separately from backup with appropriate locking and adequate
temporary capacity. Remote integrity checks do not replace a SQL restore test.
[Retention](https://restic.readthedocs.io/en/stable/060_forget.html), [repository verification](https://restic.readthedocs.io/en/stable/045_working_with_repos.html)

## Job Contract

1. Validate target inventory, credentials, free local space and remote access.
2. Export each required datastore into an isolated incomplete run directory.
3. Fail the overall job if any required export fails; never mark partial coverage
   as a successful full backup. Preserve diagnostics without credentials.
4. Produce a manifest of engine versions, database names, export times, checksums
   and application revision/config references; atomically mark the run complete.
5. Back up only completed exports and approved supporting files to restic.
6. Record the remote snapshot ID and backup coverage. Keep failed-upload exports
   for bounded retries without filling the source datastore disk.
7. Apply local retention only with confirmed offsite success and minimum recovery
   coverage. Run remote maintenance in a separate serialized job.

Restore jobs must default to an isolated target, recover roles and database data,
and run representative queries/application checks. Production overwrite is a
separately approved operation. Preserve a CLI recovery runbook that works without
Semaphore, including how to retrieve secrets when VM100 is unavailable.

## Google Drive Setup

For personal Google Drive, prefer user OAuth with a dedicated OAuth client and
unattended refresh token. Store rclone configuration securely, allow its token
refresh persistence, and never commit it or print it in job output. Choose the
narrowest practical scope and a dedicated destination folder; a folder path alone
is not a security restriction. [rclone Google Drive](https://rclone.org/drive/)

For Google Workspace Shared Drives, a service account may be suitable subject to
membership and administrator policy. A shared folder in personal My Drive is
not the same as a Shared Drive: standalone service accounts have no personal
Drive storage quota and cannot own uploaded files. [Google Drive error guidance](https://developers.google.com/workspace/drive/api/guides/handle-errors)

Drive is an offsite copy, not immutable/WORM storage. Credentials capable of
deleting repository files can destroy backups; encryption does not prevent this.
Keep recovery keys separately and consider a second independent or offline copy
for stronger deletion/ransomware protection. Verify usable quota and restore
download speed before calling the design operational.

## Deployment Gate

Before implementation, establish personal Drive versus Workspace Shared Drive,
destination and capacity, desired recovery window, approved database inventory,
and existing credential availability without exposing values. Then pilot one
test database: export, upload, restore, validate, simulate upload failure, and
verify retention selection before enabling destructive pruning.

The historical `docs/PI.md` description is preserved, with the owner-confirmed
directory-upload mechanism distinguished from unverified database consistency
and recovery coverage. This proposal and status correction are documentation-only;
no backup job, credential, database or cloud file was changed.
