---
type: Service
title: Databasus
description: Databasus deployment, authentication and backup operating notes
timestamp: 2026-10-28T19:35:00+07:00
---

# Databasus

## Runtime

- URL: `https://databasus.dungxbuif.com/`
- Swarm service: `db-management_databasus`
- Image: `databasus/databasus:v3.60.0`
- Placement: `db-ops`
- Internal port: `4005`
- State volume: `db-management-databasus-data` mounted at `/databasus-data`
- Healthcheck: `/app/main healthcheck`

The service stays private behind the existing hostname and overlay networks.
Do not reset `db-management-databasus-data` to solve a login problem.

## Admin access

The supported inventory command is run inside the live container:

```sh
docker exec -it <databasus-container> /app/main --list-admins
```

On 2026-10-28 it reported the bootstrap administrator as
`dungbui.dungbui.00@gmail.com`. The password is intentionally not recorded in
this vault. Retrieve it from 1Password before signing in; do not reuse the
CloudBeaver password and do not reset the Databasus volume.

If explicitly approved, password recovery uses the upstream CLI:

```sh
docker exec -it <databasus-container> /app/main \
  --new-password='<new-password>' \
  --email='dungbui.dungbui.00@gmail.com'
```

Store any rotated value in 1Password before closing the change.

## Backup scope and verification

There are two independent Drive paths. The `db-management` worker uploads
verified artifacts and records a `gdrive://` receipt. Databasus also already
has a Google Drive storage and a PostgreSQL logical-backup configuration in its
own state volume, but that storage is currently broken: its refresh token is
expired and the service is repeatedly logging Google Drive HTTP 401 errors for
backup writes and old-file deletion. A healthy container or HTTP status is not
backup evidence.

Verified native Drive receipts on 2026-10-28:

- PostgreSQL production: succeeded, including the common Pi5 PostgreSQL dump.
- Couchloom PostgreSQL: succeeded.
- CouchDB `_global_changes`, `_replicator`, `_users`, `homelab`, and
  `obsidian_vault`: manually queued for a full production sweep; the first four
  completed successfully during this run and `obsidian_vault` was still running
  at the time of this note.

Historical exclusions `goclaw` and `omniscan` remain intentional because those
services are retired; do not silently add them back to the production schedule.

## Current Drive failure

- Databasus log evidence starts at `2026-10-27 00:00:12 +07`.
- The failing Databasus job is a PostgreSQL logical backup for the production
  database, and the save-to-storage step fails before a valid Drive upload.
- The error is `google drive refresh token has expired` / HTTP `401`; the log
  also says no refresh token is available in the stored token.
- The separate native worker path is healthy and produced verified Drive
  receipts on 2026-10-28, so do not assume Databasus success from those receipts.

## Setup pitfalls

1. CloudBeaver and Databasus use separate accounts and persistent state.
2. CloudBeaver behind Traefik must set `CLOUDBEAVER_FORCE_HTTPS=false`; otherwise
   the internal HTTP healthcheck redirects and Swarm marks the task unhealthy.
3. The CloudBeaver source stack now points to the clean v3 workspace; old
   workspace/backup volumes and the bootstrap secret were removed.
4. Databasus CLI commands run as the image entrypoint; use a temporary helper
   container with the live container's Docker socket only for the documented
   inventory/password-recovery command, then remove the helper.
5. Never call a backup successful until the job has a verified Drive receipt;
   local staging or `/status` is not enough.
