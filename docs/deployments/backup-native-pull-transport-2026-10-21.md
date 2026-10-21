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
- `BACKUP_RUSTFS_TRANSPORT=network` is now an opt-in source contract. It runs
  the pinned AWS CLI client on the declared private network and uses the
  declared endpoint and read-only credential file. It never publishes an S3
  port or falls back to a host IP. The default remains the Pi5 container path.
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
- A live VM100 network audit found no RustFS service/container attached to
  `s3-net` or `homelab-net`. A live Pi5 audit confirmed that `rustfs` is up,
  attached only to Pi5-local Docker networks (`s3-net`, `homelab-net`,
  `proxy_net`, `edge-http-net`), exposes only internal `9000/9001` ports and
  has no host port binding. The RustFS network transport is therefore
  source-ready but not deployable until a private VM100-reachable endpoint,
  source restriction, and read-only access key are provisioned and verified.
  VM100 must not be attached to Pi5-local Docker networks, and RustFS must not
  be exposed through the public edge for backup traffic.

The source adapter and PostgreSQL credential are deployed on VM100, but the
production runner is intentionally still on the original Pi5 transport. The
Pi5-side proxy is live on private port `10.10.0.5:15984`, restricted to VM100
and the backup paths. A real export probe was started and stopped before
completion because the large `homelab` database would have continued for an
extended period; production cutover is still intentionally pending. The
runtime native PostgreSQL variables remain rolled back so the combined
`databases` class cannot enter a partial-failure state.

Live verification completed:

- valid VM100 request: non-empty HTTP `200` response;
- invalid proxy token: HTTP `401` response;
- proxy container: running as non-root with zero restarts;
- no production CouchDB data or backup marker was changed by the probe.

The exact deployment and rollback details are in
[`couchdb-backup-proxy-2026-10-21.md`](./couchdb-backup-proxy-2026-10-21.md).

## Verification

The native-transport and RustFS transport contract tests pass, including
private-network and file-backed credential assertions. Python compilation
passes for the adapters and new tests. The live direct PostgreSQL probe and
`pg_restore --list` check pass. The combined comparison remains pending on the
CouchDB read-only transport and the unavailable RustFS network endpoint. The
full local backup suite still has unrelated workstation
baseline failures: macOS has no `flock`, the local interpreter lacks `jinja2`,
and two health fixtures expect the enrolled Pi runner/marker setup. Those
failures do not exercise the new transport path; the pinned automation
execution environment remains the authoritative full-suite environment.
