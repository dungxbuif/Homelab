# Backup Scheduler Re-enable

## Remediation plan - Google Drive quota and failed timers (2026-10-07)

The first overnight window exposed two separate failure classes. The Drive
remote has usable storage, but the rclone config contains only `type`, `scope`,
`root_folder_id`, and an OAuth token; it does not contain a project-owned
`client_id`/`client_secret`. Google therefore applies the shared/default Drive
API project quota and Restic's many small object requests can return
`RATE_LIMIT_EXCEEDED`. This is API request quota, not Drive storage capacity.

The production fix is to create a project-owned OAuth desktop client in the
dedicated Google Cloud project `homelab-backup-488616`, preserve
the existing token/repository path, and install the resulting rclone config on
Pi5 without changing `DRIVE_ROOT` or initializing a new repository. The source
runner will also use bounded Drive pacing/retries and a preflight that reports
quota/access failures before an export is considered successful.

The same window found independent deployment defects: VM100's systemd runner
could not read its root-owned `runner.env`/secret files as `ubuntu`, GitLab's
native export therefore failed before upload, and the RustFS output-directory
capture was stale on the installed runtime. These are corrected separately;
retention remains blocked until all three classes produce fresh remote snapshot
IDs and post-checks pass. Existing Drive repositories and local incomplete runs
are preserved during remediation.

Implementation status: the corrected runner is installed on Pi5 and VM100;
VM100's `ubuntu` service can read its environment and backup secrets; preflight
has a bounded timeout and preserves the quota/error log; failed runs notify
Mezon immediately when the webhook is available; and the dedicated OAuth
desktop client from `homelab-backup-488616` is installed on both runtime hosts.
The existing `Homelab Backup/homelab-backups/` repository root and folder ID
were preserved. `rclone about` and a directory listing pass on both hosts.
Database run `databases-20261008-014054` now has remote snapshot
`076fb565aef9524d3f57cfb49781b688e185aa9128403775c8d0ba4e215b8d26`, a
successful post-check notification, and a fresh `databases.success` marker.
The full production `1/10` read-data check is intentionally left as a longer
maintenance audit; the run's metadata/tree check and a temporary `1/100`
read-data subset passed with a faster maintenance-only Drive pacing. Nine
duplicate pack files are reported as non-critical; prune is deferred until
all classes are healthy.

Verification gate:

1. Confirm the custom OAuth client from `homelab-backup-488616` is active and
   `rclone about` succeeds. **Passed on Pi5 and VM100.**
2. Run one database, one RustFS, and one GitLab class; each must create a
   fresh `remote/snapshot-id` and a success marker.
   **Database passed; RustFS and GitLab remain pending.**
3. Run read/check-only repository verification before retention.
4. Run retention only after all three post-checks pass; verify local cleanup
   and a Mezon result without exposing credential values.

**Date:** 2026-10-06; current verification 2026-10-13
**Status:** Timers enabled on VM100 and all three backup classes have fresh
success markers and remote snapshot IDs. The direct-root Drive migration
remains deferred because the populated, validated repositories are under
`Homelab Backup/homelab-backups/`. The health oneshot still needs a reporting
fix: its last run exited 1 before database/RustFS markers existed and logged a
unit start-time parsing warning.

Operational note: read-only Restic checks confirmed the three active legacy
repositories (database: 2 snapshots, GitLab: 1, RustFS: 1). A controlled
retention attempt was stopped after repeated Google Drive
`RATE_LIMIT_EXCEEDED` responses during snapshot listing; it performed no
prune and no local cleanup. The next scheduled retention attempt remains
bounded by the runner timeout and the cleanup gate.

## 2026-10-13 current verification

The VM100 scheduler is active and the Pi5 state directory contains these
successful class markers:

| Class | Run | Snapshot |
|---|---|---|
| Databases | `databases-20261012-180003` | `3298c3eefda04ba9e2397d024f9b359fd11d819325c436059489580a2c400961` |
| RustFS | `rustfs-20261012-213004` | `7e511fa365144b6247e63120222000c20adea72796ddc0806653cd480a6c3b82` |
| GitLab | `gitlab-20261012-193002` | `0e4c88063586aece8b924c56422ee0272779bac7b5743cc517b7a858e18b0df3` |

The class runners are not left active after completion. Retention remains
destructive and is still governed by the all-class success gate. The health
timer is enabled, but its oneshot result is not a class backup result: fix the
start-time parsing/order warning before reporting the health gate as clean.

## Overnight verification

Each VM100 backup class is logged to journald with a class-specific
`SyslogIdentifier` (`homelab-backup-databases`, `homelab-backup-gitlab`,
`homelab-backup-rustfs`, or `homelab-backup-retention`). The health service uses
`homelab-backup-health`. The morning review should capture the timer result,
service result, marker ages, and any `RATE_LIMIT`, `timeout`, `failed`, or
`cleanup` lines before changing retention or Drive paths.

Read-only review commands:

```bash
sudo journalctl -u 'homelab-backup@*.service' --since 'today 00:00' --no-pager
sudo journalctl -u homelab-backup-health.service --since 'today 00:00' --no-pager
sudo systemctl list-timers --all | grep homelab-backup
```

Do not manually run retention or remove staging directories during the review;
the runner only performs local cleanup after all three remote retention checks
pass.

## Decision

The replacement scheduler runs on VM100, which already hosts GitLab and is the
approved automation host. Pi5 remains the datastore/executor node. The scheduler
does not restore the retired `/ssd-data/backup/simple-backup.sh` cron entry.

```text
VM100 systemd timers
  |-- databases  ---- SSH ----> Pi5 runner -> PostgreSQL/CouchDB -> Drive + Mezon
  |-- rustfs     ---- SSH ----> Pi5 runner -> RustFS API --------> Drive + Mezon
  |-- gitlab     -------------> VM100 native GitLab backup ------> Drive + Mezon
  `-- retention  ---- SSH ----> Pi5 runner -> verify/check/prune all repositories
```

The global lock and status markers remain under the Pi5 staging root. Before
retention runs, the VM100 GitLab success marker is copied to that same status
directory. Every class still follows native export/API -> checksum/COMPLETE ->
restic upload/check -> Mezon post-check.

## Schedule

All times are `Asia/Ho_Chi_Minh`:

| Time | Job | Execution |
|---|---|---|
| 01:00 | Databases | VM100 timer invokes the user-owned Pi5 executor over the restricted backup SSH key |
| 02:30 | GitLab | VM100 timer runs the native Omnibus wrapper locally |
| 04:30 | RustFS | VM100 timer invokes the Pi5 RustFS API exporter |
| 05:30 | Retention | VM100 copies the GitLab marker, then invokes Pi5 retention |
| 06:15 | Health check | VM100 checks failed or overlong units, markers, incomplete runs, lock, and free space |

The Google Drive remote is `homelab1`, rooted at `Homelab Backup`; its runtime
rclone config pins `root_folder_id` to that folder so each Restic operation
does not repeatedly search Drive by name. The currently populated repositories
are retained under the existing `homelab-backups/` child, so the runtime value
is `DRIVE_ROOT=homelab-backups` and the effective repositories are
`homelab-backups/databases`, `homelab-backups/rustfs`, and
`homelab-backups/gitlab`. The empty direct-root folders remain outside the
active schedule until a controlled migration is verified. Secret values are
installed as mode `0600` files on the two runtime hosts and are never stored in
Git or echoed by the wrappers.

Remote retention and local staging retention are separate policies. Restic
keeps 14 daily, 8 weekly, and 12 monthly snapshots per repository. Only after
all three repository checks pass does the local retention step remove completed
staging runs older than the two newest runs for each class. A `.incomplete`
directory is never removed by this policy, so an interrupted export remains
available for diagnosis.

The health check is read-only. It flags a backup service that remains
`active`/`activating` for more than six hours by default, as well as failed
units, stale markers, old incomplete runs, low free space, or a held lock. It
does not kill processes or delete data; systemd's 12-hour service timeout is
the final hung-job guard, and local cleanup only runs after retention checks
pass.

## Verification plan

1. Confirm the VM100 timers are enabled and the Pi5 executor key is restricted
   to the backup entry point.
2. Run one controlled database, GitLab, and RustFS cycle manually.
3. Confirm each class has a fresh `.state/*.success` marker and one Mezon message.
4. Run retention only after all three markers are fresh; verify repository checks.
5. Confirm the next scheduled window creates no overlap and no legacy cron runs.
6. Confirm local staging keeps two completed runs per class and does not remove
   an `.incomplete` directory.
7. Confirm the health timer is enabled and sends a Mezon warning only for a
   detected problem.

## Overnight failure investigation - 2026-10-07

The first scheduled window did not complete and produced no Mezon notification.
The timer units were enabled, but the five oneshot jobs failed as follows:

- databases: Restic repository preflight rejected the Drive operation;
- gitlab: the VM100 runtime was missing the synced
  `automation/gitlab-backup/run-gitlab-backup.sh` path;
- rustfs: no complete run/manifest was available for upload;
- retention: the GitLab success marker was absent;
- health: it could not open the root-owned lock file configured under the
  unprivileged `ubuntu` service account.

The RustFS exporter also printed a verification line to stdout before its
final run path. The scheduler treated the entire captured output as a path,
so the export completed locally but the upload stage rejected it as missing
`COMPLETE`/`manifest.json`.

The health unit also had `BACKUP_HEALTH_EXPECTED_CLASSES=gitlab`, which did not
match the documented three-class health gate. The corrective deployment must
sync the GitLab native wrapper, move the shared lock to `/run/lock`, make the
health class list explicit, and run a controlled post-fix cycle before leaving
the timers enabled for the next overnight window. No retention or cleanup is
allowed until all three success markers and repository post-checks pass.

The runtime corrections were applied on 2026-10-07: the GitLab wrapper was
synced, VM100 secrets needed by the `ubuntu` service were changed to
`root:ubuntu 0640`, the VM100 lock moved to `/run/lock`, and the health unit now
quotes and checks `databases rustfs gitlab`. The runner now captures the final
path line from both database and RustFS exporters, so exporter status output
cannot corrupt the path passed to Restic.

The repaired health job ran manually and reached the failure notification path
without logging a Mezon delivery error. The controlled GitLab native export
then produced a complete local archive, but its Drive upload remained stuck in
the shared Google Drive client quota and was stopped after 7 minutes. The
database and RustFS scheduled exports also exist locally as complete runs, but
none of the three remote uploads has a fresh success marker. Retention and
local cleanup therefore remain correctly blocked.

## 2026-10-12 RustFS and GitLab upload remediation

Two independent runner defects were fixed before the next production retry:

- RustFS verification output was written to stdout alongside the completed run
  path. The exporter now writes status output to stderr, preserving stdout as
  a single path value.
- The VM100 unit uses `PrivateTmp=yes`, while Restic's per-process rclone
  config copy was created under `/tmp`. Docker runs outside systemd's private
  temporary namespace and therefore saw no `/config/rclone.conf`. The working
  copy now lives under the shared, writable application runtime directory and
  is still deleted after the Restic process exits.

The fix is accepted only after a RustFS and GitLab run each reaches
`COMPLETE`, Restic preflight, upload, `check`, remote snapshot lookup, success
marker, and Mezon post-check. Retention remains blocked until all three classes
have fresh success markers.

The first GitLab retry exposed one additional repository hygiene case: the
Drive repository contained a lock left by a process that had already died on
2026-10-06. Snapshot listing and upload completed, but the post-upload check
could not acquire the exclusive lock. The uploader now retries that check once
by running `restic unlock` only when the stale-lock signature is present and no
local Restic/Docker process remains. It then performs the check again before
accepting the snapshot. An active local process still blocks automatic unlock.

### Verification evidence

The controlled retry completed on 2026-10-12 UTC:

| Class | Run | Result | Snapshot |
|---|---|---|---|
| RustFS | `rustfs-20261012-162842` | 7 buckets exported; Restic check returned `no errors were found` | `5d7579380094031e68c7505dd3f68e65a3bd3ff050f708bcee6026c6fdc917e3` |
| GitLab | `gitlab-20261012-171259` | native archive, config/secrets, registry archive, stale-lock recovery, and Restic check passed | `3a08f373d4289ce7e53eaf1e6cf639d8d3cdee10879d1e29b49bfe15742c7dc0` |

Both classes created success markers and no backup process remained active after
completion. Retention was not manually triggered; the scheduled retention
window remains the next destructive operation and will require the fresh
database, RustFS, and GitLab markers.

## Stability hardening result

The first live check found three operational gaps before production scheduling:

- the VM100 timers were installed but disabled;
- the large CouchDB export had no request or service timeout;
- the Google Drive/rclone credential and repository path had not been validated
  as a preflight gate immediately before enabling retention.

The hardening change kept the current data flow and added bounded runtime, safe
retry behavior for transient CouchDB requests, a credential/repository
preflight, a pinned Drive root ID, and a clean post-check before enabling the
five timers. The existing Google Drive credential is reused only through the
mode-0600 runtime config; no token is copied into Git or printed.

The Drive adapter uses a conservative 5-second minimum API pacing between
requests, one request burst, and bounded retries. This is intentional: a
temporary Google Drive `RATE_LIMIT_EXCEEDED` response must slow a backup down,
not cause repository initialization or path changes. Each rclone request has a
5-minute timeout and each Restic Docker operation has a 4-hour upper bound; a
failed attempt exits and leaves the completed local export available for a
later retry.

Acceptance evidence:

1. one database run reaches `COMPLETE`, Restic snapshot verification, and
   `databases.success`;
2. the populated legacy database repository returns two Restic snapshots;
3. all four backup timers plus the health timer are enabled and their
   next-run times are visible;
4. a failed/expired credential blocks before any prune operation;
5. the first scheduled GitLab/RustFS cycle and retention run remain the final
   live-window verification still pending.

## 2026-10-08 failure remediation plan

The overnight database notifications exposed two operational hazards: an old
Restic repository lock left by a dead process, and an opaque runner exit code
(`141`) reported before the remote post-check. The intended behavior is:

- recover a repository lock only when the local host has no active Restic
  process, then run native `restic unlock` and retry the read-only preflight
  once;
- preserve preflight, upload, and post-check logs in the run directory;
- remove shell pipelines that can terminate an exporter with `SIGPIPE` while
  capturing its final path;
- keep the success marker and retention gate unchanged: no remote prune or
  local cleanup until all class post-checks pass.

Verification must include the shell contract suite, a deployed Pi5 runner
syntax check, and one real database run with `COMPLETE`, `restic-check.log`, a
remote snapshot ID, and `databases.success` present.

The remediation scripts are now deployed to Pi5. Contract tests, Python tests,
shell syntax checks, and `git diff --check` pass. Failure notifications also
include the runner stage so a future alert distinguishes export, Restic
preflight/upload, post-check, and marker failures. The live database retry is
still the final gate; its local export is complete and its paced Drive upload
is in progress.
