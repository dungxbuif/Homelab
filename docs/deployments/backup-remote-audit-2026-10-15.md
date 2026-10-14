# Backup remote audit and remaining health defects

## Read-only scope

Query each populated Restic repository on Pi5 using its installed rclone/OAuth
configuration. Use the exact snapshot ID from the most recent local success
marker, `--no-lock snapshots ID --json`, an eight-minute per-command bound and
the existing Drive pacing. Do not initialize repositories, unlock, prune,
replace credentials or remove local runs. Marker evidence alone is insufficient.

| Class | Latest recorded run | Snapshot |
| --- | --- | --- |
| databases | databases-20261013-180002 | ac5fdaecd374394f754f4dae0045ad959273f1ed94ecfb47f470ecae874a6974 |
| gitlab | gitlab-20261013-193000 | b28a0e84f859a97d95931e0470d5c070a4a98c320587c7a7e12f616d083abae3 |
| rustfs | rustfs-20261013-213001 | 6cbcc04238ccfae6cac06d66bbaa303aa4b701de1bcf17537de18783cc57a29b |

VM100 reports successful terminal results for these three class units.
Retention remains failed from 2026-10-13 23:53:47 UTC (exit 1); its old failure
must not be erased just because the RustFS writer ownership was repaired.
Remote read results and restore evidence are pending at the start of this note.

## Health reporting defects confirmed

The VM100 health unit explicitly expects all three class markers in its local
status directory. Database and RustFS markers actually live on Pi; only GitLab
is produced locally on VM100. This causes false missing-marker warnings. The
health wrapper must query Pi through the restricted backup SSH command boundary
and combine those results with local scheduler/unit/GitLab checks, not ignore
remote classes or fabricate copied success markers.

`check-backup-health.sh` reads ActiveEnterTimestamp for both active and
activating services. A long-running oneshot stays activating and has no current
active-enter timestamp. Use the process start monotonic timestamp and host
uptime for duration, with explicit unknown/error handling; avoid parsing locale
dependent date strings. Do not hide a genuine failed retention service.

The next scheduled database job is 2026-10-15 01:00 +07. Do not start a long
destructive retention rehearsal ahead of that window. A remote snapshot listing
proves snapshot existence only, not complete payload integrity or restore.

## Remote results

The bounded read-only query completed with exit 0. All three exact IDs above
were returned by their remote repositories, not merely found in local markers.

| Class | Snapshot time returned by Restic (UTC) |
| --- | --- |
| databases | 2026-10-13T18:30:19.185010847Z |
| gitlab | 2026-10-13T19:34:30.989624533Z |
| rustfs | 2026-10-13T21:35:07.416305568Z |

No repository was initialized, unlocked or pruned; no backup class was rerun.
These are the previous nightly window's snapshots, not a claim about the next
scheduled run. Remaining gates: retrieve and validate snapshot payloads, perform
isolated restores, correct the two health-reporting defects, and verify an
entire retention pass after fresh successful backups. Preserve the failed
retention unit as evidence until that pass actually succeeds.

## Health repair implementation plan

Allow exactly one additional restricted SSH operation, `health`. Pi executes
its local read-only health script for database/RustFS markers, staging and lock,
with scheduler-unit inspection and recursive remote checks disabled. VM100
checks scheduler units and only its local GitLab marker, then combines Pi output
into one health result/notification. SSH failure or remote warnings must remain
visible and nonzero. No arbitrary command or path is accepted by the SSH guard.

Use ExecMainStartTimestampMonotonic and `/proc/uptime` for active/activating job
age. Tests cover activating oneshots, missing timestamps and failed remote
health. Compare existing live hashes before deployment; back up each replaced
script. Reload only the health unit configuration, not the backup timers or
running backup jobs. A real failed retention unit must still fail the audit.

Deployment note: production inventory sets `ansible_become: false`, which
overrides the task keyword. Explicit task-scoped `ansible_become: true` is
required only for the system unit copy and daemon reload. Script installation
continues as the owning backup user; no timer or running backup is restarted.

## Health repair verification

Deployed Pi first, then VM100 through `backup-health-repair.yml`. The VM retry
was idempotent for scripts and changed only the health unit; daemon reload
succeeded. All 38 Python backup tests passed, including five health tests.
Live systemd Environment now selects `gitlab` locally and enables remote Pi
health. All five backup timers retain their scheduled times.

Live manual check returned exit 1 intentionally: the only reported failure
was `homelab-backup@retention.service`. Pi health passed, database marker age
79539s, RustFS 71223s, GitLab 78716s. No false missing marker remained.
This check did not send a notification and did not reset the failed unit.
Retention journal confirms permission-denied deletion of old RustFS staging
under `rustfs-20261012-162842`; an end-to-end retention pass is still required
after the ownership repair. Snapshot existence is not restore verification.

Public documentation is unchanged: this modifies internal backup supervision,
not an application API or user-facing configuration contract.

Follow-up ownership audit: the old `rustfs-20261012-162842` staging tree is
755 MiB and all entries now belong to `dungxbuif`; the 13 RustFS run directories
also report that owner. No data was deleted by this audit. Add the five health
regression tests to the CI validation job so the cross-host contract remains
covered after publication. Scheduler foundation changes are preserved separately.
