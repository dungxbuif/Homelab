---
type: Service
title: Databasus
description: Databasus runtime, verification agent, Drive storage, admin access and credential mapping
generated:
  by: claude-code/opus-5.5
  at: "2026-10-31T00:00:00+07:00"
stale_after: "2027-01-29T00:00:00+07:00"
---

# Databasus

## Source

| Field | Value |
|---|---|
| Upstream | https://github.com/databasus/databasus (unverified repo URL; image `databasus/databasus`) |
| Pinned version | `databasus/databasus:v3.64.0@sha256:dca80ac1…` |
| Deploy source | `homelab-ops/automation/stacks/db-management/stack.yml` (stack `db-management`) |
| Repo docs | none (third-party) |

## Runtime

- URL: `https://databasus.dungxbuif.com/` (private, behind Pi5 Traefik)
- Swarm service: `db-management_databasus` (stack `db-management`, source
  `homelab-ops/automation/stacks/db-management/stack.yml`)
- Image: `databasus/databasus:v3.64.0@sha256:dca80ac1bf555b706d33cd9506a6422387a34fb22eea5ca1cacfc52babd58d2e`
- Placement: VM110 `db-ops`; internal port `4005`
- State volume: `db-management-databasus-data` → `/databasus-data`
- Healthcheck: `/app/main healthcheck`; version: `/api/v1/system/version`

Never reset `db-management-databasus-data` to fix a login problem. Logical
backup configs must use retention value `3_MONTH` (the old invalid
`THREE_MONTH` panics the cleaner).

**Rollback:** the pre-upgrade volume archive is
`/ssd-data/infra/backups/version-upgrade-20261031/databasus/databasus-volume-before-retention-fix.tgz`
(SHA-256 `471f340e…c322748`). Restore the previous image `v3.60.0` only
together with that archive, because the retention values were migrated.

## Jobs and coverage

15 PostgreSQL jobs on the shared Pi5 cluster: `bds_prod`, `family_tree`,
`gitlabhq_production`, `goclaw`, `homelab`, `macocr`, `mypocket`, `n8n`,
`netbird`, `netbird_activity`, `netbird_idp`, `omniscan`, `relayhub`,
`whiteboard`, `postgres` (`PostgreSQL production`). `relayhub_v1_staging_20261030`
(live RelayHub v1) has no job listed (unverified — check and add).
`goclaw` and `omniscan` belong to retired services.

Scheduled `After backup` restore verification is enabled and passed on
2026-10-31 for `n8n`, `homelab`, `relayhub`, `netbird`, `netbird_activity`,
`netbird_idp`. GitLab verification is disabled (size). The other jobs are
dump/upload evidence only and need a scope decision before adding load to the
single-job agent. Databasus does not replace a `pg_dumpall --globals-only`
export of roles and grants.

### Audit warning — 2026-10-31

The entries above are historical evidence and do not constitute a current
all-jobs pass. During the live audit, Databasus began returning Google Drive
HTTP `401 Invalid Credentials` while finding or creating `databasus_backups`.
The six post-upgrade manual backup attempts hit that provider failure. The
admin password currently stored in 1Password also does not authenticate against
the live service. Do not claim 100% backup or restore coverage until the OAuth
storage is re-authorized and every in-scope job has a fresh successful backup
and an isolated successful restore. The full evidence and remaining gaps are
tracked in [the 2026-10-31 audit](../deployments/databasus-audit-2026-10-31.md).

## Restore verification agent

- `pi-verifier-1` in workspace `Homelab Production`; official ARM64 binary at
  `/ssd-data/infra/services/databasus-verification/verification-agent`.
- Host unit `databasus-verification-agent.service` (enabled), user
  `dungxbuif` with Docker group access; private config
  `databasus-verification.json` (mode 0600) in the same directory. The token is
  never stored in this vault.
- Capacity 2 CPU / 2048 MB / 20 GB scratch / **1 concurrent job**. It creates
  disposable PostgreSQL containers; Docker `userns-remap` is disabled on Pi5
  (enabling it is a separate hardening change).
- Checks and procedures: [Databasus backup operations](../runbooks/databasus-backup-operations.md).

## Google Drive storage and OAuth

- Databasus writes to its own `databasus_backups` folder (scope `drive.file`),
  placed inside the `Homelab Backup` folder
  <https://drive.google.com/drive/folders/1XzEaTjaBnDU0smPxuzkEnw5s2ScRn3OW>
  (owner `dungbui.dungbui.00@gmail.com`). The editor has no folder-ID field.
- Google Cloud project `homelab-backup-488616`.
- Databasus needs a **Web** OAuth client (callback
  `https://databasus.dungxbuif.com/storages/google-oauth`): `Databasus Homelab
  Drive`, client ID
  `271302542235-0903rf6alokfpb3qr2v1ku105601gpaf.apps.googleusercontent.com`.
  The Desktop client `Homelab Backup rclone` is for rclone/native worker only.
- If uploads fail with `google drive refresh token has expired` / HTTP 401,
  re-authorize the storage through the Web callback, test, then run
  **Backup now**.

## Notifier

`Mezon Homelab` webhook notifier: backup-failed and healthcheck-unavailable
events. Delivery was tested; a real failure event has not been injected. The
URL lives in 1Password `Homelab Secret`, never here.

## Admin access

```sh
docker exec -it <databasus-container> /app/main --list-admins
```

Bootstrap admin: `dungbui.dungbui.00@gmail.com`; password in 1Password
(separate from CloudBeaver). Password recovery, only if approved:

```sh
docker exec -it <databasus-container> /app/main \
  --new-password='<new-password>' --email='dungbui.dungbui.00@gmail.com'
```

Store any rotated value in 1Password before closing the change.

## Credential mapping (1Password vault `Homelab Secret`)

- `Databasus`: admin URL, username, password
- `Homelab Backup Google Drive OAuth`: Web client ID/secret, project/folder metadata
- Native worker Swarm secret `db-management-drive-credentials-v2`
  (`clientId`, `clientSecret`, `refreshToken`, `databaseFolderId`)
- Worker webhook: `MEZON_WEBHOOK_URL_FILE=/run/secrets/db_management_mezon_webhook`

## Pitfalls

1. CloudBeaver (`db-management_cloudbeaver` 26.2.3) and Databasus have separate
   accounts and state.
2. CloudBeaver behind Traefik needs `CLOUDBEAVER_FORCE_HTTPS=false`; 26.2.3 has
   no `curl`, so its healthcheck is a Bash TCP check.
3. The db-management worker's `gdrive://` receipts are a separate path; never
   infer Databasus health from them, or vice versa.
4. A backup is successful only with a `Successful` row plus a new payload and
   `.metadata` pair in Drive.

## Gate status

| Gate | State | Evidence / exception (expiry) |
|---|---|---|
| G0 Intake | not assessed | part of db-management stack |
| G1 Build | partial | upstream image pinned by digest |
| G2 Security | not assessed | |
| G3 Runtime | partial | in stack, healthcheck present; limits (unverified) |
| G4 Data | partial | own state volume has only the 2026-10-31 pre-upgrade archive; no scheduled backup or restore record |
| G5 Observability | not assessed | |
| G6 Release | not assessed | |
| G7 Docs | partial | this doc |
| G8 Operate | not assessed | |
