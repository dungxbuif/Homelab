# DB-management core audit — 2026-10-25

## Deployed

- Swarm stack `db-management` remains on VM110 (`db-ops`); no new service was
  placed on Pi5.
- API, worker and web were rebuilt and deployed from the current workspace.
  The worker release is `core-20261025-db-audit`.
- Bootstrap config `db-management-bootstrap-v2` now catalogs:
  - CouchDB homelab, with the existing exclusions;
  - PostgreSQL as a CloudBeaver bookmark;
  - Redis production as a monitor-only source.
- Swarm secrets were created from existing server-side sources for Redis and
  the Mezon webhook. Values were not copied to git, images, logs or this file.

## Live evidence

Checked through the Pi5 LAN ingress with an explicit diagnostic address override
(`db-management.dungxbuif.com -> 10.10.0.5`):

| Check | Result |
| --- | --- |
| API liveness | `GET /health` returned `200` |
| Worker readiness | `GET /health/ready` returned `200` with a fresh worker heartbeat |
| CouchDB | Catalogued and existing status/database routes remain live |
| Redis | `status`, bounded `INFO` and `metrics` returned `ok`; no key browsing or arbitrary command route |
| UI | New monochrome DB-management page returned successfully |
| Mezon | Durable notification probe changed outbox state `pending -> sent`, one attempt, no error |
| Databasus | HTTPS system health returned `200`; local application storage is healthy |

## Backup status and migration boundary

The legacy runner's Google Drive remote is readable. The `databases` Restic
repository had 15 snapshots; the newest observed snapshot was
`2026-10-20T23:38:08.925821092Z`. This proves remote read access only. Legacy
backup timers remain disabled, so it is not current protection.

Databasus still has no verified Google Drive OAuth/storage configuration,
backup job, remote snapshot, or isolated restore evidence. The new app therefore
keeps backup inventory explicitly `unsupported` instead of presenting an empty
successful list. PostgreSQL remains a bookmark until Databasus is enrolled and
its restore gate passes. CouchDB remains owned by the old native/Restic runner
until a fixed provider bridge and restore verification exist.

Next acceptance gate:

1. Configure Databasus from its private UI with the project-owned Google OAuth
   client and redirect URI; do not import the old rclone token blindly.
2. Enroll one disposable PostgreSQL database, run a backup, verify Drive remote
   read and isolated restore.
3. Decide the fixed CouchDB provider boundary, run one complete export/upload/
   restore cycle, then map the source's `backupProviderId` and only then retire
   the legacy owner.

No production backup schedule, retention prune, or restore was enabled by this
 audit.
