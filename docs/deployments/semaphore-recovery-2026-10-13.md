---
type: Deployment
title: "Semaphore History and Metadata Recovery"
description: "Restore the private provisioning UI history and normalize the live database provisioning form without adding a second scheduler"
timestamp: 2026-10-13T00:00:00+07:00
---

# Semaphore History and Metadata Recovery

**Status:** Completed and verified on 2026-10-13.
**Host:** Pi5 `rpivn` (`10.10.0.5`).
**Runtime:** `semaphoreui/semaphore:v2.19.12`, Swarm service
`semaphore_semaphore`, one replica.

## Problem

The UI showed an empty task history even though the single project and
`db-provision` template were still present. The history rows had been removed
during the earlier cleanup. The form labels and task messages also exposed
internal survey/API names, which made the database/user workflow difficult to
understand.

## Recovery

1. Preserved the live SQLite database, WAL, and SHM files before any write.
2. Restored the six retained task records from:

   ```text
   /ssd-data/infra/semaphore/data/database.sqlite.precleanup-20261006-222206.sqlite
   ```

3. Kept exactly one project, one template, one user, and one access key.
4. Renamed the template to **Provision database and application owner** and
   added a description that explains database creation, owner creation, smoke
   test, Swarm secret, and backup-catalog enrollment.
5. Replaced raw survey labels with operator-facing labels such as **Database
   engine**, **Database name**, **Application or service**, **Target
   environment**, **Backup policy**, and **Swarm secret reference**.
6. Added readable task messages derived from status/engine/database name, while
   keeping credentials out of task metadata and output.
7. Restarted the service and verified `200 pong` from the health endpoint.

## Current contract

Semaphore is a private database/user provisioning UI. It is not a backup
scheduler and it does not own a Docker socket. The internal
`homelab-provisioner_provisioner` service remains the only Docker API holder;
its service has no published port. Successful PostgreSQL/CouchDB provisioning
smoke-tests the owner and enrolls the resource in the canonical backup catalog.
The VM100 systemd timers remain the only backup schedule.

Use the [database provisioning runbook](../runbooks/db-provisioning.md) for the
form values and the [runtime inventory](./runtime-inventory-2026-10-13.md) for
the current image/version and replica state.

## Verification

```text
semaphore_semaphore: 1/1
homelab-provisioner_provisioner: 1/1
health endpoint: 200 pong
history: six retained task rows visible
project/template/user/access-key count: 1/1/1/1
```

The pre-recovery and pre-label SQLite copies remain on the Pi5 for rollback and
audit. No database resource or application credential was created by this
metadata recovery.
