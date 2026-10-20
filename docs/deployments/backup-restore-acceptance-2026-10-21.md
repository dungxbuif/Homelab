---
type: Deployment Evidence
title: "Database instance restore acceptance"
description: "Scratch restore verification for the VM100 CouchLoom PostgreSQL instance backup"
timestamp: 2026-10-21T00:00:00+07:00
---

# Database Instance Restore Acceptance

## Scope

This is a non-production restore drill for the `database-instances` class. It
does not certify the separate `databases`, RustFS, GitLab or configuration
restore paths.

## Evidence

| Field | Result |
| --- | --- |
| Source run | `database-instances-20261020-202507` |
| Restic snapshot | `164f85eb25e03f936a9cba0c29185d00712bf4cfbc155d1818726224ea3e72c7` |
| Payload | CouchLoom PostgreSQL `couchloom.dump`, `postgres.dump`, `globals.sql` |
| Restore target | Temporary PostgreSQL container on VM100, no published port |
| Engine | `pgvector/pgvector:0.8.6-pg17-bookworm` |
| Native restore | `pg_restore --exit-on-error --no-owner --no-acl`, exit `0` |
| Query check | `SELECT 1` passed |
| Restored relations | `226` |
| Vector extension | `0.8.6` |
| Cleanup | Temporary container, network and 27 MiB scratch directory removed |

The first compatibility probe with `postgres:16` failed closed with
`unsupported version (1.16) in file header`. The dump was created with a newer
PostgreSQL client, so the drill was repeated with the production-compatible
PostgreSQL 17/pgvector image. A second probe without the `vector` extension was
also rejected as expected; the final run used the image that supplies the
required extension.

## Result and limits

The `database-instances` snapshot is restorable and queryable in isolation.
No production database, volume, network or service was changed. RTO was not
measured with a wall-clock stopwatch in this run; RPO is bounded by the source
snapshot timestamp recorded in the success marker and Restic metadata.

Remaining acceptance work is tracked in `docs/BACKLOG.md`: full PostgreSQL /
CouchDB class coverage, RustFS, GitLab, a monthly unattended drill and a
second off-site target remain open.
