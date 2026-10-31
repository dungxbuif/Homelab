---
type: Runbook
title: Databasus backup operations
description: Verify, clean up and onboard PostgreSQL backups safely
timestamp: 2026-10-31T02:54:00+07:00
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
7. The verification agent is online and the database has at least one
   successful restore verification; scheduled verification is enabled when the
   database is in the approved service set.

The first six checks prove dump and upload. They do not prove restore. Cluster
roles and grants still need a separate `pg_dumpall --globals-only` export.

## Verify the current setup

1. Query the live PostgreSQL cluster and record every non-template database.
2. In Databasus, compare that list with the database job list; there must be no
   database without a job and no stale job for a retired database.
3. Open each job's **Backups** tab and check the newest row is `Successful`.
4. Check the newest payload plus `.metadata` pair in the Drive folder.
5. Confirm the notifier is attached and the backup-failure/healthcheck-unavailable
   events are enabled.
6. Record restore status separately. A `Successful` backup without a
   `Successful` restore verification is still only dump/upload evidence.

## Verification agent operations

The current agent is `pi-verifier-1` on Pi5. It runs as the host unit
`databasus-verification-agent.service` from
`/ssd-data/infra/services/databasus-verification/` with one concurrent job.
The token and generated JSON config are private host state; never copy them
into this vault, chat, shell history or a deployment manifest.

Read-only checks:

```sh
ssh pi 'systemctl is-active databasus-verification-agent.service'
ssh pi 'systemctl status databasus-verification-agent.service --no-pager'
ssh pi 'journalctl -u databasus-verification-agent.service -n 80 --no-pager'
```

In Databasus, use **Settings → Verification agents** to confirm `Online` and
the reported capacity. For a controlled proof, open a database's **Backups**
tab, click the safety/verify action on a known successful backup, choose
**Queue check**, then record the result under **Verifications**. A passing
check must show `Successful`, `pg_restore exit code 0`, and restored schema/table
counts. The current n8n proof is recorded in the 2026-10-31 upgrade ledger.

Do not queue all large databases at once. The Pi5 agent is intentionally
single-job; GitLab remains excluded from this wave because its backup set is
too large for the requested maintenance window.

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
6. Add the database to the service inventory, enable the approved verification
   interval, and run one restore verification after the next successful backup.

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
- An offline verification agent is a restore-coverage gap, not a reason to call
  the backup failed; pause scheduled checks and repair the agent before
  claiming restore coverage.
- If a new job cannot create a read-only user, document the accepted privilege
  risk and plan a separate least-privilege credential review.
