---
type: Deployment Evidence
title: "GitLab native backup restore acceptance"
description: "Scratch PostgreSQL restore and archive verification for the latest GitLab backup"
timestamp: 2026-10-21T00:00:00+07:00
---

# GitLab Native Backup Restore Acceptance

## Evidence

| Field | Result |
| --- | --- |
| Source run | `gitlab-20261020-190208` |
| Restic snapshot | `a0cbb341f856d2ef324cb57b4ddb29dc4eab23f22c690e9c0d131531cac26fb` |
| GitLab version | `18.11.11` |
| Native archive | 8,741,672,960 bytes; SHA-256 manifest passed |
| Archive structure | 105 tar entries; registry gzip passed |
| Database payload | `db/database.sql.gz`; gzip stream passed |
| Restore target | Temporary PostgreSQL 17/pgvector container on VM100, no published port |
| Native SQL restore | `psql -v ON_ERROR_STOP=1`, exit `0` |
| Query check | `SELECT 1` passed |
| Restored relations | `928` public tables |
| Restored application records | `3` users, `5` projects |
| Extensions | `amcheck`, `btree_gist`, `pg_trgm`, `plpgsql` |
| Cleanup | Scratch container, database and temporary logs removed |

The archive was inspected without changing the production GitLab container.
The SQL payload was streamed from the verified native archive into an isolated
database. No host port, production volume, production database or GitLab
service was reused.

## Limits

This proves the latest GitLab archive and its PostgreSQL payload are readable
and restorable at the database layer. It does not boot a complete disposable
GitLab application or prove repository-object and registry-object serving
through the GitLab UI. Those objects are present in the native archive and
remain covered by the archive checksum/structure checks. A full application
boot rehearsal remains a separate, higher-cost recovery exercise.
