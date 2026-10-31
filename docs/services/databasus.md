---
type: Service
title: Databasus
description: Databasus deployment, authentication and backup operating notes
timestamp: 2026-10-31T02:54:00+07:00
---

# Databasus

## Runtime

- URL: `https://databasus.dungxbuif.com/`
- Swarm service: `db-management_databasus`
- Image: `databasus/databasus:v3.64.0@sha256:dca80ac1bf555b706d33cd9506a6422387a34fb22eea5ca1cacfc52babd58d2e`
- Placement: `db-ops`
- Internal port: `4005`
- State volume: `db-management-databasus-data` mounted at `/databasus-data`
- Healthcheck: `/app/main healthcheck`

The service stays private behind the existing hostname and overlay networks.
Do not reset `db-management-databasus-data` to solve a login problem.

## Version maintenance — 2026-10-31

- A fresh named-volume archive was captured before the maintenance retry at
  `/ssd-data/infra/backups/version-upgrade-20261031/databasus/databasus-volume-before-retention-fix.tgz` (`29280340` bytes; SHA-256
  `471f340e7b4a82877d7192e4d5c8cfad1e7cf668d8dcc0123948503f7c322748`).
- The embedded PostgreSQL state contained `15` logical backup configs with the
  invalid value `THREE_MONTH`. A transaction changed them to the upstream
  supported value `3_MONTH`; no database, backup payload, storage credential or
  encryption key was removed.
- `v3.64.0` is now running `1/1`. `/api/v1/system/version` reports `3.64.0`,
  the health endpoint reports the internal DB working, migrations report no
  pending work, and the retention cleaner starts without a new panic.
- This proves the release/runtime and metadata migration. It does not replace
  the separate provider-authenticated backup and isolated restore gate below.

## Restore verification agent — 2026-10-31

- Registered the Databasus verification agent `pi-verifier-1` in the
  `Homelab Production` workspace and installed the official ARM64 binary on
  Pi5 at `/ssd-data/infra/services/databasus-verification/verification-agent`.
- The agent is supervised by the host unit
  `databasus-verification-agent.service`, enabled at boot, and runs as
  `dungxbuif` with Docker-group access. Its private config file is
  `/ssd-data/infra/services/databasus-verification/databasus-verification.json`
  with mode `0600`; the agent token is not stored in this vault or emitted in
  the service command line.
- Capacity is deliberately bounded at `2` CPU, `2048` MB RAM, `20` GB scratch
  disk and `1` concurrent restore. The agent reports `Online` in Databasus and
  the unit is `active (running)` after installation.
- The first manual verification used the latest PostgreSQL `n8n` backup and
  completed `Successful`: `pg_restore` exit code `0`, one schema, `153`
  tables, `52.58 MB` restored, and `2s` restore duration. This closes one real
  restore path, not merely a checksum or upload check.
- A second controlled n8n run after the `v3.64.0` upgrade also passed the
  provider path: the 2026-10-31 02:53 backup completed `Successful` with a
  `1.91 MB` payload for a `147.82 MB` database, then `After backup` queued an
  automatic restore check that completed `Successful` with `pg_restore` exit
  code `0`, one schema, `190` tables, `54.76 MB` restored and `2s` restore
  duration.
- Scheduled `After backup` verification is enabled for `n8n`, `homelab`,
  `relayhub`, `netbird`, `netbird_activity`, and `netbird_idp`. GitLab's
  verification schedule remains disabled because its maintenance and backup
  set is intentionally skipped for size.
- The agent needs Docker access to create disposable PostgreSQL containers;
  its startup log reports that Docker `userns-remap` is disabled on Pi5. Keep
  the agent single-job and treat enabling user namespace remapping as a
  separate security-hardening change after compatibility testing.

### Approved service database verification wave

After the n8n proof, each approved service database was backed up again and
its `After backup` restore verification was allowed to complete:

| Database | New backup | Restore result |
|---|---:|---|
| `n8n` | `1.91 MB` payload / `147.82 MB` DB | `Successful`, `pg_restore 0`, `190` tables, `54.76 MB`, `2s` |
| `homelab` | `0.18 MB` payload / `1.6 MB` DB | `Successful`, `pg_restore 0`, `63` tables, `10.16 MB`, `0s` |
| `relayhub` | `0.1 MB` payload / `1.41 MB` DB | `Successful`, `pg_restore 0`, `30` tables, `9.15 MB`, `0s` |
| `netbird` | `0.1 MB` payload / `1.79 MB` DB | `Successful`, `pg_restore 0`, `39` tables, `9.74 MB`, `0s` |
| `netbird_activity` | `0.01 MB` payload / `0.08 MB` DB | `Successful`, `pg_restore 0`, `2` tables, `7.49 MB`, `0s` |
| `netbird_idp` | `0.02 MB` payload / `0.37 MB` DB | `Successful`, `pg_restore 0`, `13` tables, `7.77 MB`, `0s` |

Every row showed `Successful` and `Verified` in the Databasus backup list. The
remaining Databasus jobs belong to other or retired applications and need a
separate scope decision; they were not silently added to this maintenance
wave.

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
editor. The Databasus folder was moved into the supplied `Homelab Backup`
folder on 2026-10-28 and the Drive breadcrumb plus new artifacts were verified
there. Databasus will continue using the same child folder for later jobs.

The Databasus backup list showed a fresh `Successful` encrypted logical backup
for each active PostgreSQL job and the corresponding payload plus metadata files
were visible in Drive. This proves the dump/upload path, not a restore. The
verification agent is online and all six approved service databases now have
post-upgrade `Successful` + `Verified` evidence; the remaining jobs still
need an explicit restore-coverage decision.

On 2026-10-28 the shared Pi5 PostgreSQL cluster was reconciled to 15
Databasus jobs, each with a successful backup run: `bds_prod`, `family_tree`,
`gitlabhq_production`, `goclaw`, `homelab`, `macocr`, `mypocket`, `n8n`,
`netbird`, `netbird_activity`, `netbird_idp`, `omniscan`, `relayhub`,
`whiteboard`, and `postgres` (`PostgreSQL production`). Databasus jobs do not
replace a separate `pg_dumpall --globals-only` export for cluster roles and
grants.

### Notification path

The `Mezon Homelab` webhook notifier is configured in Databasus and attached
to `PostgreSQL production`. The notifier accepts all supported event types;
the production backup config currently emits `Backup failed` notifications,
and healthcheck-unavailable notifications remain enabled. The test
notification completed successfully on 2026-10-28. That test proves webhook
delivery only; no deliberate backup failure has been injected to test the
event path. The webhook URL is intentionally not recorded here; retrieve it
from the `Homelab Secret` credential mapping when rotating or recreating the
notifier.

## Adding a new database

Databasus does not discover new PostgreSQL databases automatically. Every new
database must be registered once, and catalog enrollment alone does not create
the Databasus job:

1. Open **Databases → Add database** and select the engine and backup type.
2. Enter the host, port, database name, and least-privilege backup user; run
   the connection test.
3. In **Backup config**, enable backups, select `Google Drive backup`, choose
   the interval/time and retention, then save.
4. Select `Mezon Homelab` under **Notifiers settings** and save.
5. Run **Backup now** and confirm the result is `COMPLETED` with no failure
   message and a new artifact under `Homelab Backup/databasus_backups`.
6. Record the database in the inventory, enable the intended verification
   interval, and run one restore verification. The first successful backup is
   not a restore acceptance gate by itself.

Existing database schedules are independent. Changing the shared PostgreSQL
cluster or creating a new database does not add a Databasus job; repeat the
procedure above and record the database in the service inventory.

For the full acceptance gate, verification checklist, new-database procedure,
and artifact cleanup rules, use the [Databasus backup operations runbook](../runbooks/databasus-backup-operations.md).

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
