# PostgreSQL collation reconciliation

Date: 2026-10-21

## Finding

The Pi5 PostgreSQL cluster was checked database by database using
`pg_database_collation_actual_version`. All application databases stored the
runtime `en_US.utf8` collation version `2.36`. Only the maintenance database
`postgres` stored `2.41` while the current runtime reported `2.36`.

## Applied change

Refreshed the collation version and reindexed only the `postgres` database:

```sql
ALTER DATABASE postgres REFRESH COLLATION VERSION;
REINDEX DATABASE postgres;
```

No application database, role, connection endpoint, or service restart was
part of this change.

## Verification contract

The post-change query reports `2.36` for both `datcollversion` and
`pg_database_collation_actual_version()` on `postgres`. All application
databases remain at `2.36`, and the following application databases each
returned `SELECT 1`: `bds_prod`, `family_tree`, `gitlabhq_production`,
`goclaw`, `homelab`, `macocr`, `mypocket`, `n8n`, `netbird`,
`netbird_activity`, `netbird_idp`, `omniscan`, `relayhub`, and `whiteboard`.

## Result

The warning is resolved. No index or connectivity error was observed, and no
application service restart was required.
