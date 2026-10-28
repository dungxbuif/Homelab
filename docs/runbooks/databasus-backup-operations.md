---
type: Runbook
title: Databasus backup operations
description: Verify, clean up and onboard PostgreSQL backups safely
timestamp: 2026-10-28T23:50:00+07:00
---

# Databasus backup operations

For an agent-executable version of the PostgreSQL production onboarding flow,
use the local skill `creating-postgres-databasus-backup`.

## Acceptance gate

A PostgreSQL database is onboarded only when all of these are true:

1. The database exists in the shared Pi5 cluster inventory.
2. It has its own Databasus job pointing at the exact database name.
3. The job passes the connection test and has Google Drive storage selected.
4. `Mezon Homelab` is attached for backup-failure and healthcheck-unavailable alerts.
5. **Backup now** finishes with `Successful`.
6. A new payload and `.metadata` artifact is visible below
   `Homelab Backup/databasus_backups`.
7. Restore verification is completed when a verification agent is available.

The first five checks prove dump and upload. They do not prove restore. Cluster
roles and grants still need a separate `pg_dumpall --globals-only` export.

## Verify the current setup

1. Query the live PostgreSQL cluster and record every non-template database.
2. In Databasus, compare that list with the database job list; there must be no
   database without a job and no stale job for a retired database.
3. Open each job's **Backups** tab and check the newest row is `Successful`.
4. Check the newest payload plus `.metadata` pair in the Drive folder.
5. Confirm the notifier is attached and the backup-failure/healthcheck-unavailable
   events are enabled.
6. Record restore status separately. `No verification agent registered` means
   restore is not verified, even when backups are successful.

Useful inventory command:

```sh
ssh pi 'docker exec postgres psql -U admin -d postgres -Atc \
  "SELECT datname FROM pg_database WHERE NOT datistemplate ORDER BY datname"'
```

## Add a new PostgreSQL database

After the database is created in the shared cluster:

1. Create a dedicated Databasus database job for the exact database name.
2. Use the existing Google Drive storage and `Mezon Homelab` notifier.
3. Test the connection and save the backup schedule/retention.
4. Run **Backup now**.
5. Verify `Successful` in Databasus and a payload/metadata pair in the target
   Drive folder.
6. Add the database to the service inventory and run restore verification once
   the verification agent is deployed.

Databasus does not auto-discover databases created inside PostgreSQL.

## Artifact cleanup

Keep the newest successful payload and matching `.metadata` file for each job.
Remove only files that are demonstrably stale duplicates, failed attempts, or
artifacts belonging to retired jobs. Never clean by deleting the whole folder.

After cleanup, refresh the folder and verify that the newest pair for every
active job is still present. Google Drive deletion through the UI moves files to
Trash; retain the Trash window until the next successful backup has been
verified.

## Failure handling

- A healthy Databasus page is not backup evidence; inspect the job's backup row
  and Drive artifact.
- A storage/authentication error must be fixed and followed by **Backup now**;
  do not mark the job healthy from a previous native-worker receipt.
- A missing verification agent is a restore-coverage gap, not a reason to call
  the backup failed.
- If a new job cannot create a read-only user, document the accepted privilege
  risk and plan a separate least-privilege credential review.
