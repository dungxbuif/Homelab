# MyPocket datastore DNS migration (2026-09-15)

## Intended change

The operator approved moving both MyPocket API and worker off Pi5 LAN
datastore URLs. Both currently use PostgreSQL `10.10.0.5:5432/mypocket`
and Redis `10.10.0.5:16379/1`. Update only the hostname and port to
`pgbouncer:6432/mypocket` and `redis-prod:6379/1` on `homelab-net`.
Preserve URL scheme, username, password, database name, Redis index, query
parameters, images, application code, and persisted data. Do not publish
new host ports.

## Verification and rollback

Before changing either service, authenticate to both DNS endpoints from
each task's network namespace, confirm PostgreSQL `SELECT 1` and Redis
`PONG`, and save only redacted old URL locations. Update API first; wait for
healthy task and check its datastore connections and public money route.
Update worker only after API passes; check task, worker logs, both datastore
probes, and public route again. If one service regresses, revert only that
service's two URL values; do not clear PostgreSQL or Redis data.

Public docs do not change: this is an internal endpoint migration with no
new API, domain, or user-facing configuration.

## Runtime secret names

MyPocket production stores S3/RustFS credentials under
`MYPOCKET_SECRETS` in gitignored `local_vars.json`. Keep both naming
families populated there:

- Canonical backup/restore names: `S3_ACCESS_KEY_ID`,
  `S3_SECRET_ACCESS_KEY`.
- Runtime service names used by the deployed API and worker:
  `S3_ACCESS_KEY`, `S3_SECRET_KEY`.

Both alias pairs point to the same bucket-scoped RustFS credential. Do not
print the values in docs, shell history, or deployment logs.

## Executed result

Both old task namespaces authenticated to `pgbouncer:6432` (`SELECT 1`)
and `redis-prod:6379` (`PONG`) before service updates. API was updated first;
its replacement task was healthy with zero restarts, and the public money
route returned 200. Worker was then updated; its replacement task reported
`worker ready in production`, zero restarts, `SELECT 1`, and `PONG`. Both
service URLs now use Docker DNS and retain PostgreSQL `mypocket`, Redis
DB `/1`, URL query parameters, and credentials. No data reset occurred.
