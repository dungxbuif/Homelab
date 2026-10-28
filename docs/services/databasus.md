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

## Google Drive target and OAuth project

- Backup folder: <https://drive.google.com/drive/folders/1XzEaTjaBnDU0smPxuzkEnw5s2ScRn3OW>
- Google Cloud project: `homelab-backup-488616`
- Project console: <https://console.cloud.google.com/welcome?project=homelab-backup-488616>
- The folder is owned by `dungbui.dungbui.00@gmail.com` and contains the
  `databases` child folder.
- Existing OAuth desktop client: `Homelab Backup rclone`.

Databasus requires a Web OAuth client because it uses the callback
`https://databasus.dungxbuif.com/storages/google-oauth`. The older Desktop
client is for the native worker/rclone flow and cannot be used for this web
callback. The Databasus client is named `Databasus Homelab Drive` in the same
project; its non-secret client ID is
`271302542235-0903rf6alokfpb3qr2v1ku105601gpaf.apps.googleusercontent.com`.
Never put either client secret or any refresh token in this document,
Git, Swarm environment variables, or chat logs.

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
own state volume. On 2026-10-28 the storage was re-authorized through the Web
OAuth callback; the storage test returned success and a new PostgreSQL backup
completed successfully. A healthy container or HTTP status is not backup
evidence.

Databasus creates and manages its own `databasus_backups` folder using the
`drive.file` scope. The supplied Homelab Drive folder is the native worker's
target; Databasus does not currently expose a folder-ID field in its storage
editor, so do not assume the two backup trees are the same.

### Notification path

The `Mezon Homelab` webhook notifier is configured in Databasus and attached
to `PostgreSQL production`. The notifier accepts all supported event types;
the production backup config currently emits `Backup failed` notifications,
and healthcheck-unavailable notifications remain enabled. The test
notification completed successfully on 2026-10-28. The webhook URL is
intentionally not recorded here; retrieve it from the `Homelab Secret`
credential mapping when rotating or recreating the notifier.

## Adding a new database

Databasus does not discover new PostgreSQL databases automatically. Every new
database must be registered once:

1. Open **Databases → Add database** and select the engine and backup type.
2. Enter the host, port, database name, and least-privilege backup user; run
   the connection test.
3. In **Backup config**, enable backups, select `Google Drive backup`, choose
   the interval/time and retention, then save.
4. Run **Backup now** and confirm the result is `COMPLETED` with no failure
   message. The first successful run is the acceptance gate for the new DB.

Existing database schedules are independent. Changing the shared PostgreSQL
cluster or creating a new database does not add a Databasus job; repeat the
procedure above and record the database in the service inventory.

## Credential mapping

- 1Password vault: `Homelab Secret`
- `Databasus`: admin URL, username, and password
- `Homelab Backup Google Drive OAuth`: Web client ID and client secret, plus
  project/folder metadata
- Native worker secret: `db-management-drive-credentials-v2`, with
  `clientId`, `clientSecret`, `refreshToken`, and `databaseFolderId`
- Runtime webhook mapping: `MEZON_WEBHOOK_URL_FILE=/run/secrets/db_management_mezon_webhook`

Verified native Drive receipts on 2026-10-28:

- PostgreSQL production: succeeded, including the common Pi5 PostgreSQL dump.
- Couchloom PostgreSQL: succeeded.
- CouchDB `_global_changes`, `_replicator`, `_users`, `homelab`, and
  `obsidian_vault`: manually queued for a full production sweep; the first four
  completed successfully during this run and `obsidian_vault` was still running
  at the time of this note.

Historical exclusions `goclaw` and `omniscan` remain intentional because those
services are retired; do not silently add them back to the production schedule.

## Historical Drive failure

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
