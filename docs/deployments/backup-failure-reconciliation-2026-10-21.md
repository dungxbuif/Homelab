# Backup failure reconciliation

Date: 2026-10-21

## Scope

The recent Captain Hook failures were reviewed against VM100 systemd journals,
the deployed backup scripts, current timer state, and a fresh health run.

## Findings

- The `databases` failure at 19:13 UTC was a transient deployed-script syntax
  error in the older Pi5 backup-runner copy (`upload-restic.sh`, line 84).
  The corrected release was deployed before the later run at 23:12 UTC; the
  database backup completed successfully at 23:40 UTC.
- The `monitoring-drift` failure at 00:08 UTC was the stale pre-repair unit
  invocation that referenced a missing audit helper. The deployed unit now
  includes both the wrapper and `audit-monitoring-targets.py`, and a later
  target audit succeeded.
- Several `signal` results occurred while long-running retention or backup
  work was being interrupted. The repository checks that completed reported no
  Restic integrity errors. These historical failures remain visible in the
  journal but are not active failed units.

## Current verification

At 2026-10-21 01:01 UTC, a manual `homelab-backup-health.service` run exited
successfully with:

- VM100: `38.7 GB` free, `81%` used, lock free;
- Pi5: `304.7 GB` free, `35%` used, lock free;
- current success markers present for GitLab, database-instances, configs,
  restore-drill, databases, and RustFS;
- no failed systemd units.

The historical failed runs are retained for auditability. No backup payload,
Restic repository, or database was deleted during this reconciliation.
