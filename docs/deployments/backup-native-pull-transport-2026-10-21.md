---
type: Deployment
title: "Native backup pull transport"
description: "Source contract for moving PostgreSQL, CouchDB and RustFS export work from Pi5 to VM100"
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
- `BACKUP_POSTGRES_GLOBALS_TRANSPORT=network` keeps globals on the same private
  `pg-net` path and uses `backup_ro` with `--no-role-passwords`; no admin
  credential leaves PostgreSQL or enters the VM100 credential file.
- `BACKUP_COUCHDB_TRANSPORT=network` is reserved for the approved GET-only
  proxy design below. It will run the curl client image on `homelab-net` and
  never expose port 5984 directly to VM100.
- `BACKUP_RUSTFS_TRANSPORT=network` is now the production RustFS path. It runs
  the pinned AWS CLI client on `s3-net` and uses the private endpoint plus the
  read-only credential file. It never publishes an S3 port or falls back to a
  host IP. The Pi5/container path remains the explicit rollback mode.
- Client image, network, endpoint and credential-file settings are runtime
  inputs in `/etc/homelab-backup/runner.env`; they are not committed.
- The source transport refuses network mode when any required setting is
  absent. Existing Pi5 mode remains the rollback path.

## Rollout gate

The rollout gates are split by datastore. Before enabling the remaining
database transport on VM100:

1. create and verify the least-privilege PostgreSQL/CouchDB backup identities;
2. enroll the reviewed client image digests and root-owned credential files on
   VM100;
3. run the CouchDB proxy export beside the current Pi5 export and compare
   document/attachment counts and restore results; and
4. only then retire the Pi5 `databases` export and remove its Restic/Drive
   secrets. RustFS has already passed its own cutover gate.

No production service is stopped by the source transport. No live runtime was
changed by this document or its implementation.

## Database authentication decision

The Pi5 PgBouncer instance uses `auth_file` with SCRAM for application traffic,
but native backup does not depend on that auth path. The `backup_ro` role is
created directly in PostgreSQL with no login-administration, database-creation,
superuser, replication, or write-data privileges and is tested through
`postgres-pg:5432` on `pg-net`. No application credential is changed.

### CouchDB ACL limitation and proxy design

CouchDB has no native database-level read-only member role: a non-admin member
can also write documents. A live enrollment probe confirmed that `_users`
security cannot be changed for this purpose (`403`), so direct member
enrollment is rejected. The selected design is a Pi5-local GET-only
proxy that keeps CouchDB admin credentials inside the data host, accepts a
separate VM100 token, allows only the backup `GET` paths, and rejects all
mutating methods. It is deployed on private port `10.10.0.5:15984` and is not
exposed through Traefik, Rathole or a public domain.

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
- A live Pi5 and VM100 audit confirmed that `s3-net` is a shared, attachable
  Swarm overlay. From a disposable VM100 client, `rustfs` resolved to
  `10.0.31.2` and its S3 API returned the expected unauthenticated `403`.
  RustFS is also attached to Pi5's `homelab-net`, `proxy_net` and
  `edge-http-net`, exposes only internal `9000/9001` ports and has no host port
  binding. RustFS has passed its production gate: a bucket-scoped read-only
  key was provisioned, the native pull was compared with the Pi5 export, and
  an isolated restore passed. VM100 uses only `s3-net`; backup traffic does
  not use the public edge.
  Evidence: [RustFS network preflight](./rustfs-network-preflight-2026-10-21.md).

The source adapter and PostgreSQL credential are deployed on VM100. The
RustFS class now runs locally on VM100 when
`BACKUP_RUSTFS_TRANSPORT=network`; removing that setting rolls back to the
Pi5 path. The Pi5-side CouchDB proxy is live on private port
`10.10.0.5:15984`, restricted to VM100 and the backup paths. The combined
`databases` class remains on the Pi5 path until its CouchDB comparison gate
passes.

Live verification completed:

- valid VM100 request: non-empty HTTP `200` response;
- invalid proxy token: HTTP `401` response;
- proxy container: running as non-root with zero restarts;
- `obsidian_vault` export and isolated restore matched `49,210` documents;
- the full inventory probe was stopped by the VM100 disk-safety guard at about
  83% usage while entering the large `homelab` database;
- no production CouchDB data or backup marker was changed by either probe.

The exact deployment and rollback details are in
[`couchdb-backup-proxy-2026-10-21.md`](./couchdb-backup-proxy-2026-10-21.md).

## Verification

The native-transport and RustFS transport contract tests pass, including
private-network and file-backed credential assertions. Python compilation
passes for the adapters and new tests. The live direct PostgreSQL probe and
`pg_restore --list` check pass. RustFS native export covered 7 buckets and
3,115 checksum entries; no key/size object was missing against the latest Pi5
run, and a scratch `mac-ocr` restore verified 62 objects. The remaining
comparison is the full CouchDB inventory, especially the large `homelab`
database. The
full local backup suite still has unrelated workstation
baseline failures: macOS has no `flock`, the local interpreter lacks `jinja2`,
and two health fixtures expect the enrolled Pi runner/marker setup. Those
failures do not exercise the new transport path; the pinned automation
execution environment remains the authoritative full-suite environment.
