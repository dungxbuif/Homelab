# Backup Runner

The runner serializes each backup class behind one host lock. A class always
follows this order:

```text
native/API export -> COMPLETE + manifest + checksums -> restic backup/check
-> post-check -> one Mezon status
```

`run-class.sh` supports `databases`, `database-instances`, `rustfs`, `gitlab`,
and `configs`. The `database-instances` class selects only cataloged PostgreSQL
instances for the owning host (currently CouchLoom on VM100) and invokes the
native `pg_dumpall`/`pg_dump` adapter through its private Docker container. The
Pi `databases` class similarly selects only same-host instances, so it cannot
accidentally export a remote container. The GitLab class receives a completed
directory produced by the VM100 native wrapper; it never copies a live GitLab
filesystem itself. The separate `weekly-integrity` job performs deep checks
without exporting or pruning. `run-retention.sh` is separate and prunes only after
repository checks, using the Pi class-specific restic repositories.

Required runtime environment is secret-free in the repository and must be
provided by Semaphore/Docker secrets:

```text
RESTIC_PASSWORD_FILE
RCLONE_CONFIG_FILE
BACKUP_LOCAL_RCLONE_BIN
RCLONE_REMOTE
DRIVE_ROOT
MEZON_WEBHOOK_URL_FILE
RUSTFS_CREDENTIALS_FILE  # required for the rustfs class
BACKUP_STATUS_ROOT       # optional; defaults to <staging-root>/.state
```

The runner does not stop, scale, recreate, or remove production services. Exit
code `75` means another class already owns the global lock and the scheduler
should retry later without overlapping it. VM100 scheduled classes wait up to
one hour for the lock (`BACKUP_SCHEDULE_LOCK_WAIT_SECONDS`) and retry every 30
seconds; direct Pi executor calls remain non-blocking.

Restic integrity checks are split by cadence. Every upload confirms remote
snapshot metadata and defers the full structural `restic check` to retention
and deep-verify. Set `RESTIC_POST_UPLOAD_CHECK=structural` only for an explicit
one-off upload that must check inline. Set `RESTIC_READ_DATA_SUBSET=1/10` only
for a scheduled deep verification window.
The same variable opts retention into a payload read; without it, retention
performs structural verification before pruning. This keeps the nightly
Google Drive path bounded while preserving periodic data-integrity checks.
Drive requests are serialized with burst `1` and a `100ms` minimum pacer
delay by default. Override `RCLONE_DRIVE_PACER_MIN_SLEEP` deliberately for
quota-sensitive operations; do not restore the historical `10s` default
without recording the expected runtime impact.

After a class passes its remote post-check, `run-class.sh` writes a short
success marker under `BACKUP_STATUS_ROOT`. Starting a new class attempt removes
that class marker. `run-retention.sh` requires the three Pi markers to be
recent (26 hours by default) before it invokes any destructive prune. VM100
then verifies and prunes the `database-instances` repository and its local
staging under the same scheduler workflow.

Local staging is bounded separately from Google Drive retention. After the
three Pi repositories pass their retention checks, VM100 also verifies the
additional-instance repository. The runner keeps the two most recent
completed staging runs per class and removes older completed runs. It never
removes a run before `COMPLETE` exists and never removes an `.incomplete`
directory automatically. GitLab and additional-instance staging are cleaned
on VM100; shared database and RustFS staging are cleaned on Pi5.

`check-backup-health.sh` is a non-destructive operator check. It reports
failed backup units, backup units that remain `active`/`activating` beyond the
class-specific maximum runtime, stale success markers, old `.incomplete`
directories, an active global lock, and low free space. A lock held by a
recognized in-limit backup is reported as `state=running` and does not create
a false failure; a held lock without an active backup unit is a failure. The
scheduled health timer runs after the retention window and sends a Mezon
warning only when a problem is found; it never deletes a run. The scheduled
service also sends a daily success summary; ad-hoc checks stay quiet on
success unless `BACKUP_HEALTH_NOTIFY_SUCCESS=true` is set.

Health also warns at 85% filesystem usage and fails at 92%, in addition to the
10 GiB minimum-free-space gate. Override with `BACKUP_HEALTH_DISK_WARN_PERCENT`
and `BACKUP_HEALTH_DISK_FAIL_PERCENT` when a host has a different capacity policy.

The fallback active-job threshold defaults to six hours and can be changed
with `BACKUP_HEALTH_ACTIVE_MAX_AGE_SECONDS`. Known classes use tighter
defaults: databases two hours, database-instances 30 minutes, RustFS and
retention 90 minutes, and GitLab five hours. The databases allowance reflects
the observed PostgreSQL plus CouchDB export duration (about 90 to 105 minutes)
and prevents a healthy long-running export from producing a false alert. Each class can be overridden with its
`BACKUP_HEALTH_<CLASS>_MAX_AGE_SECONDS` variable. These limits are deliberately
shorter than the systemd service timeout, so a stuck job is reported before
systemd eventually kills it.

The `configs` class is not enabled yet. Its schedule is declared but disabled.
It requires a verified Pi5 archive
in `BACKUP_CONFIGS_PI_ARCHIVE`, combines it with the explicit VM100 inventory,
and only then uploads one atomic encrypted Restic run. Calling the class without
that archive fails before any upload.

VM100 writes class-specific backup output to journald. Review the overnight
window with `journalctl -u 'homelab-backup@*.service'`; the health unit uses
`journalctl -u homelab-backup-health.service`. A normal review checks service
result, marker age, and Drive errors before any manual retry or cleanup.

For Google Drive, the runtime rclone config pins `root_folder_id` on the
active remote to the `Homelab Backup` folder. The currently populated,
validated repositories remain under its existing `homelab-backups/` child, so
the runtime value is `DRIVE_ROOT=homelab-backups` and the effective paths are
`homelab-backups/databases`, `homelab-backups/database-instances`,
`homelab-backups/rustfs`, `homelab-backups/gitlab`, and (after first enablement)
`homelab-backups/configs`. This avoids an extra Drive folder-search call on
every Restic operation while the direct-root migration is pending.

The runtime config must use the dedicated project-owned Google OAuth client
from Google Cloud project `homelab-backup-488616`. A config that
contains only `type`, `scope`, `root_folder_id`, and `token` uses rclone's
shared/default project and can hit `RATE_LIMIT_EXCEEDED` even when Drive has
plenty of storage. Uploads are paced and retried, but retry policy is not a
replacement for the project-owned client. The uploader records preflight and
post-upload check logs inside the run directory and refuses to report success
without a verified remote snapshot ID.

The VM100 systemd unit keeps `PrivateTmp=yes`. Restic therefore must not create
the Docker-mounted rclone working copy under `/tmp`, because Docker's daemon
namespace cannot see systemd's private temporary directory. Set
`RCLONE_CONFIG_WORK_ROOT` to `/home/ubuntu/.homelab-backup-runtime` (or use the
staging root fallback); all ancestors satisfy the no-follow ownership check,
the path is writable by the service and visible to Docker. The working copy
remains mode `0600` and is removed after each Restic process.

Exporter stdout is a machine-readable contract: database and RustFS wrappers
must emit only the completed run directory on stdout. Verification and
progress messages belong on stderr. This prevents a successful RustFS export
from being passed to Restic as a multi-line, invalid directory path.
