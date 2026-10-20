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

Enrollment and runtime publication both take the same `/run/lock/homelab-backup.lock`
global lock used by the scheduled runner. Catalog registration also uses its
separate catalog lock while the reviewed generation is being activated.
The enrollment generation publishes `policies.yaml` together with the catalog
and reviewed scripts. This is required because an older live Pi policy file may
still predate the `db-instance-default` class; candidate validation must fail
closed rather than silently enroll an instance that cannot be scheduled.

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

The first live enrollment attempt on 2026-10-15 stopped during candidate
validation because the live Pi policy catalog lacked `db-instance-default`.
Nothing was published. The playbook now stages, validates and atomically
publishes the reviewed policy catalog with a private rollback copy before the
next attempt.

The corrected retry succeeded with `ok=12 changed=5 failed=0`. The live catalog
contains both `relayhub-dedicated` and `couchloom`, the new instance policy is
present, and the active generation symlinks resolve to their retained private
generation. Enrollment now repeats that resolution and catalog validation as a
post-check.

The first VM100 runtime publication stopped before systemd because the
playbook's global `become: false` left the lock ownership implicit. A later
attempt showed Ubuntu's `fs.protected_regular=2` correctly rejects root opening
a lock file owned by the service user inside sticky `/run/lock`. The playbook
now uses root only to ensure that lock is owned by `ubuntu` with mode `0660`,
then invokes the atomic publication explicitly through `runuser -u ubuntu`,
matching the systemd backup unit and avoiding Ansible become-precedence
differences.

The first native VM100 run then stopped before Restic because an older runner
environment/drop-in still pointed at root-owned `/var/lib/homelab-backup/runtime`.
The next retry showed the no-follow helper also rejects group-writable
`/opt/apps` ancestors. The runtime-config playbook now converges both
environment and systemd to `/home/ubuntu/.homelab-backup-runtime`, whose full
ancestor chain and owner satisfy that helper; the failed runs produced no
remote snapshot or success marker.

## Live acceptance

The controlled VM100 run completed on 2026-10-15 as
`database-instances-20261015-112854` with `rc=0`. The native payload was
complete (7 files, about 27.4 MiB), Restic created snapshot
`fa3aa6c6606183910918917784e12546e08f77668ccb8efd58cc791dfbd42943`, and the
remote post-check passed `restic check --read-data-subset=1/10`. The run keeps
its remote metadata under `remote/` and the `database-instances.success` marker
was written only after the Mezon post-check.

The VM100 timer is now enabled and active, with the next scheduled run at
20:00 UTC (03:00 local). It is intentionally separated from the 18:00 UTC
database backup, whose observed runtime is about 92 to 104 minutes. The VM100
health service completed with `Result=success`; its
health check covers the local `gitlab` and `database-instances` markers and the
Pi5 health result. The Pi5 health check also passes with a free backup lock.

An older Pi5 remote-restore rehearsal was found holding the global lock for
over three hours while its target remained at 8 KiB and produced no restore
payload. Only that exact rehearsal process tree was terminated with `TERM`;
production backup data and containers were not touched. The rehearsal remains
unaccepted and must be rerun later with a bounded timeout before declaring
restore acceptance complete.

This is an internal backup/operations change. No public API or public user
documentation changes are required.
