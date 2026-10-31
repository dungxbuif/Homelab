---
type: Deployment audit
title: Databasus PostgreSQL backup and restore audit
description: Evidence-led audit of the Databasus backup path and PostgreSQL restore coverage
timestamp: 2026-10-31T11:40:39+07:00
---

# Databasus PostgreSQL backup and restore audit — 2026-10-31

## Decision

**FAIL / not safe to claim 100% coverage yet.** Databasus itself is healthy,
but the provider-authenticated backup path is currently failing. The
verification agent is online, and six application databases have historical
post-upgrade restore evidence, but the full PostgreSQL set does not currently
have a fresh successful backup plus a successful isolated restore for every
job.

Do not mark the PostgreSQL backup gate done until a fresh backup and restore
check has passed for every in-scope Databasus job.

## Evidence captured

- Audit window: 2026-10-24 through 2026-10-31 (ICT).
- Databasus service: `db-management_databasus`, image `v3.64.0`, Swarm
  placement `db-ops`, replicas `1/1`.
- `https://databasus.dungxbuif.com/` and
  `/api/v1/system/health` return HTTP `200` from Pi5.
- Databasus version endpoint reports `3.64.0`.
- `databasus-verification-agent.service` is `active`; the agent heartbeat and
  claim loop continue to return HTTP `200`/`204`.
- No new `THREE_MONTH` retention-cleaner panic was found after the metadata
  repair and current task startup. The historical invalid value was changed to
  the supported `3_MONTH` value before this audit.

## Blocking failure

From the live Databasus service log, beginning at `2026-10-30T19:51:02Z`,
Google Drive operations fail with HTTP `401` / `Invalid Credentials` while
finding or creating `databasus_backups`. The log includes the stored OAuth
token structure and shows that Databasus is attempting a refresh, but the
provider rejects the credentials.

The manual backup attempts for `n8n`, `homelab`, `relayhub`, `netbird`,
`netbird_activity`, and `netbird_idp` in that wave therefore cannot be used as
fresh upload proof; each hit the same Drive authentication failure.

The 1Password `Databasus` item currently contains an admin password that the
live service rejects (`password is incorrect`). No password reset or volume
replacement was performed during this audit because that would be a separate
credential mutation and could invalidate the only remaining admin session.

## PostgreSQL scope reconciliation

The shared PostgreSQL cluster currently contains these 16 non-template
databases:

`bds_prod`, `family_tree`, `gitlabhq_production`, `goclaw`, `homelab`,
`macocr`, `mypocket`, `n8n`, `netbird`, `netbird_activity`, `netbird_idp`,
`omniscan`, `postgres`, `relayhub`, `relayhub_v1_staging_20261030`, and
`whiteboard`.

The Databasus state is documented as having 15 jobs:

`bds_prod`, `family_tree`, `gitlabhq_production`, `goclaw`, `homelab`,
`macocr`, `mypocket`, `n8n`, `netbird`, `netbird_activity`, `netbird_idp`,
`omniscan`, `relayhub`, `whiteboard`, and `postgres` (`PostgreSQL production`).

`relayhub_v1_staging_20261030` is a newly observed database and has no
documented Databasus job. It must be explicitly classified as staging and
enrolled, or explicitly excluded with an owner and expiry date; it must not be
silently omitted from a “whole cluster” claim.

## Restore coverage

The following six databases have recorded post-upgrade `Successful` backup
and `Verified` restore results through the single-concurrency agent:

| Database | Restore evidence |
| --- | --- |
| `n8n` | `pg_restore` exit `0`, 190 tables |
| `homelab` | `pg_restore` exit `0`, 63 tables |
| `relayhub` | `pg_restore` exit `0`, 30 tables |
| `netbird` | `pg_restore` exit `0`, 39 tables |
| `netbird_activity` | `pg_restore` exit `0`, 2 tables |
| `netbird_idp` | `pg_restore` exit `0`, 13 tables |

No equivalent post-upgrade restore result is recorded here for
`bds_prod`, `family_tree`, `gitlabhq_production`, `goclaw`, `macocr`,
`mypocket`, `omniscan`, `whiteboard`, or `postgres`. The six rows above are
real restore evidence, but they are not evidence for the remaining jobs.

## Required close-out sequence

1. Recover or intentionally rotate the Databasus admin credential and store
   the verified value in 1Password.
2. Re-authorize the Databasus Google Drive storage through the supported Web
   OAuth callback; do not reuse the separate native-worker token as proof.
3. Run a fresh **Backup now** for all 15 Databasus jobs, one at a time, and
   record `Successful`, payload, matching `.metadata`, and Drive location.
4. Queue one isolated restore verification for every fresh artifact. Keep the
   agent at one concurrent restore; include GitLab if it remains in scope.
5. Classify/enroll `relayhub_v1_staging_20261030` before making a whole-cluster
   statement.
6. Export PostgreSQL globals/roles separately; logical database backups do not
   prove cluster-wide roles and grants.

Until all six steps have evidence, the status remains **PARTIAL / FAIL**, not
“100% confirmed”.
