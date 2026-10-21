---
type: Deployment
title: "Native backup pull transport"
description: "Source contract for moving PostgreSQL and CouchDB export work from Pi5 to VM100"
timestamp: 2026-10-21T00:00:00Z
---

# Native backup pull transport

## Purpose

B9 requires VM100 to perform the data export over the existing private Docker
networks. The current adapter still uses `docker exec` against the Pi5
PostgreSQL and CouchDB containers, so moving only the Restic retention job is
not enough.

## Source contract

- The existing container transport remains the default and is unchanged.
- `BACKUP_POSTGRES_TRANSPORT=network` runs the PostgreSQL client image on
  `pg-net`, connecting directly to `postgres-pg:5432` with a dedicated
  `backup_ro` credential file. It never publishes a database port or uses a
  host IP. PgBouncer is deliberately not in the backup path.
- `BACKUP_COUCHDB_TRANSPORT=network` runs the curl client image on
  `homelab-net`, connecting to the Docker service name `couchdb`. It uses a
  dedicated read-only CouchDB credential file and never exposes port 5984.
- Client image, network, endpoint and credential-file settings are runtime
  inputs in `/etc/homelab-backup/runner.env`; they are not committed.
- The source transport refuses network mode when any required setting is
  absent. Existing Pi5 mode remains the rollback path.

## Rollout gate

This source change is not the cutover. Before enabling it on VM100:

1. create and verify the least-privilege PostgreSQL/CouchDB backup identities;
2. enroll the reviewed client image digests and root-owned credential files on
   VM100;
3. run one native pull beside the current Pi5 export and compare manifests,
   object/document counts and restore results for one week; and
4. only then disable Pi5 `databases`/`rustfs` export and remove its Restic and
   Drive secrets.

No production service is stopped by the source transport. No live runtime was
changed by this document or its implementation.

## Database authentication decision

The Pi5 PgBouncer instance uses `auth_file` with SCRAM for application traffic,
but native backup does not depend on that auth path. The `backup_ro` role is
created directly in PostgreSQL with no login-administration, database-creation,
superuser, replication, or write-data privileges and is tested through
`postgres-pg:5432` on `pg-net`. No application credential is changed.

## Current runtime inventory

The read-only audit on 2026-10-21 found:

- Pi5 still has `/ssd-data/infra/backup/runner.env`,
  `/ssd-data/infra/backup/secrets/rclone.conf`, and
  `/ssd-data/infra/backup/secrets/restic-password` (all mode `0600`); this is
  why the final secret-removal step is not marked done.
- VM100 has its root-owned `/etc/homelab-backup/runner.env` and Drive config,
  with all four primary backup timers active.
- PostgreSQL now has the dedicated least-privilege `backup_ro` identity. VM100
  stores its credential in `/etc/homelab-backup/secrets/postgres-backup.env`
  with root-owned `640` permissions. A disposable VM100 client verified login
  and a custom-format `pg_dump` over `pg-net` to `postgres-pg:5432`.
- VM100 service membership is consistent with the preflight: application
  consumers use `pg-net`/`s3-net`; CouchLoom remains the documented
  `homelab-net` exception.

## Verification

The three native-transport contract tests pass, including private network and
file-backed credential assertions. Python compilation passes for both adapters
and the new tests. The live direct PostgreSQL probe and `pg_restore --list`
check pass. The full local backup suite still has unrelated workstation
baseline failures: macOS has no `flock`, the local interpreter lacks `jinja2`,
and two health fixtures expect the enrolled Pi runner/marker setup. Those
failures do not exercise the new transport path; the pinned automation
execution environment remains the authoritative full-suite environment.
