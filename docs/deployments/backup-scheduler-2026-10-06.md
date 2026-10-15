# Backup Scheduler Re-enable

**Date:** 2026-10-06
**Status:** Being enabled after the 2026-10-05 online rehearsal

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

The Google Drive remote is `homelab1`, rooted at `Homelab Backup`; the runner
uses the existing three repositories under `homelab-backups/`. Secret values are
installed as mode `0600` files on the two runtime hosts and are never stored in
Git or echoed by the wrappers.

## Verification plan

1. Confirm the VM100 timers are enabled and the Pi5 executor key is restricted
   to the backup entry point.
2. Run one controlled database, GitLab, and RustFS cycle manually.
3. Confirm each class has a fresh `.state/*.success` marker and one Mezon message.
4. Run retention only after all three markers are fresh; verify repository checks.
5. Confirm the next scheduled window creates no overlap and no legacy cron runs.
