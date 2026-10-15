# Multi-instance PostgreSQL backup rollout

## Decision

The shared Pi5 PostgreSQL container remains the `databases` backup class. The
separate RelayHub PostgreSQL container is already enrolled in that class as a
same-host instance. CouchLoom PostgreSQL runs on VM100, so it must not be
silently executed by the Pi5 adapter or by a same-named container there.

Add a `database-instances` class for explicitly cataloged PostgreSQL instances
whose backup host is VM100. The class will:

- run `pg_dumpall --globals-only`, `pg_dump --format=custom`, and
  `pg_restore --list` through the local CouchLoom container;
- use the existing inventory and validation rules, with a host-scoped export
  so a remote instance cannot be mistaken for a local container;
- publish a separate Restic repository under `homelab-backups/database-instances`;
- verify the remote snapshot and send one Mezon post-check notification;
- retain only completed local runs according to the database-instance policy;
- participate in health and retention prerequisites without stopping CouchLoom
  or exposing PostgreSQL.

The inventory contains instance metadata only: instance ID, host, container,
backup user, database names, application and lifecycle. Passwords remain in
the container/runtime secret boundary and are never added to the catalog.

## Affected contracts

- `backup/inventory.yaml`: add the VM100 CouchLoom instance.
- `backup/scripts/common.py`: validate all instance metadata, and select only
  instances matching the host requested by an exporter.
- `backup/scripts/run-instance-backup.py`: export the selected host-scoped
  instances with an immutable manifest.
- `automation/backup-runner/run-class.sh`: upload and post-check the new class.
- VM100 scheduler, health, retention prerequisites and local cleanup: schedule
  and gate the new class.
- `backup/README.md` and `automation/backup-runner/README.md`: document the
  native multi-host backup behavior and restore boundary.

## Verification plan

1. Unit-test host selection, invalid/duplicate metadata, empty databases and
   atomic incomplete runs.
2. Run the existing backup, scheduler, health, retention and shell contract
   suites in the pinned execution environment.
3. Deploy only after the current CI pipeline is green.
4. Run a native VM100 CouchLoom export, verify the remote post-check and Mezon
   status, then restore its completed snapshot into a disposable network-less
   PostgreSQL container using the exact installed image.
5. Keep the existing local checkpoints until remote restore acceptance passes;
   do not delete production containers or data as part of enrollment.

This is an internal backup/operations change. No public API or public user
documentation changes are required.
