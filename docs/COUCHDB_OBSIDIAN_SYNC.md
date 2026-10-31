---
type: Runbook
title: "CouchDB Obsidian Sync"
description: "Current deployment, client settings, verification and recovery for the Pi5 CouchDB LiveSync backend"
timestamp: 2026-10-31T00:00:00+07:00
---

# CouchDB Obsidian Sync

CouchDB on the Raspberry Pi 5 is the Obsidian Self-hosted LiveSync backend and
the source of truth for CouchLoom. It has no host port; public traffic comes
through the VPS edge.

## Deployment

| Item | Value |
| ---- | ----- |
| Host | Pi5 `rpivn` (`10.10.0.5`) |
| Stack | Compose `infra` at `/ssd-data/infra` |
| Container | `couchdb` |
| Image | `couchdb:3.5.3@sha256:bed314d1…` |
| Internal port | `5984` |
| Data | `/ssd-data/infra/couchdb/data` |
| Local config / CORS | `/ssd-data/infra/couchdb/local.d/obsidian.ini` |
| Backup proxy | `couchdb-backup-proxy`, GET/HEAD-only, LAN `10.10.0.5:15984`, VM100 backup relay only |

Request path:

```text
Internet -> VPS gateway-traefik (HostSNI allow-list, 103.82.21.202)
-> Rathole -> Pi5 edge-traefik-pi5 -> couchdb:5984
```

## Endpoints

| Endpoint | Exposure |
| -------- | -------- |
| `https://sync-db.dungxbuif.com` | Internet endpoint for LiveSync; path-restricted to `/`, `/_session` and `/obsidian_vault…` |
| `https://couchdb.dungxbuif.com` | LAN-only (`lan-only` middleware) |

## Databases

| Database | Purpose / access |
| -------- | ---------------- |
| `obsidian_vault` | Main Obsidian vault sync (~49k docs). `_security`: admin = CouchDB admin; member = `obsidian_sync` user/role. Anonymous `401`. |
| `homelab` | LiveSync copy of this Homelab vault (doc ids are repo paths), member `homelab_sync`. Decision: private/admin-only, no public `sync-db` route. Whether a `/homelab` path is currently present on the `sync-db` router is (unverified). |
| `_users`, `_replicator`, `_global_changes` | System |

## Client settings

| Setting | Personal vault | Homelab vault |
| ------- | -------------- | ------------- |
| URI | `https://sync-db.dungxbuif.com` | `https://couchdb.dungxbuif.com` (LAN; `sync-db` `/homelab` path unverified) |
| Database | `obsidian_vault` | `homelab` |
| User | `obsidian_sync` | `homelab_sync` |

The Homelab vault is documentation-only for LiveSync: keep `syncOnlyRegEx` at
`^docs(?:/|$)` so source checkouts and generated files never sync.

## Credentials

Never store passwords in vault notes.

- `/ssd-data/infra/couchdb/.env` — admin bootstrap and CouchDB secrets (`0600`).
- `/ssd-data/infra/couchdb/obsidian-sync.env` — non-admin sync user (`0600`).
- Local reference: `local_vars.json` -> `COUCHDB_SECRETS`.

## CORS

Allowed origins: `app://obsidian.md`, `capacitor://localhost`,
`http://localhost`, `http://127.0.0.1`, `https://couchdb.dungxbuif.com`.

## Verification

On Pi5:

```bash
docker ps --filter name=couchdb
docker logs --tail 80 couchdb
```

Public path through the VPS:

```bash
curl -k --resolve sync-db.dungxbuif.com:443:103.82.21.202 \
  -u "$COUCHDB_SYNC_USER:$COUCHDB_SYNC_PASSWORD" \
  https://sync-db.dungxbuif.com/obsidian_vault
```

Expected: authenticated `200`, anonymous `401`, CORS preflight from
`app://obsidian.md` `204`.

## Headless LiveSync CLI

CouchLoom on VM100 uses the vendored LiveSync common library directly against
this database and does not run a second sync node. The optional local CLI
runner is documented in the CouchLoom checkout at
`/home/dungxbuif/workspace/projects/couchloom/docs/LOCAL_LIVESYNC.md`
(`tools/livesync/livesync.sh doctor | remote-status | sync`).

If LiveSync reports the remote database is locked and this device is not
accepted, stop. Never `unlock-remote` from an empty or unverified local
database; rebuild on the trusted Obsidian device first.

## Recovery

```bash
cd /ssd-data/infra
docker compose up -d couchdb
docker logs --tail 120 couchdb
```

Routes are managed in the Pi5 Traefik edge and the VPS HostSNI allow-list;
change them only through the route catalog in `homelab-ops`. Backups: the
`databases` class exports `obsidian_vault` (restore verified 2026-10-31, see
[backup repair](./deployments/backup-repair-2026-10-31.md)); a recurring
schedule is open in [BACKLOG](./BACKLOG.md).

## Related

- [Raspberry Pi 5 Datastore Spec](./PI.md)
- [Stack](./STACK.md)
