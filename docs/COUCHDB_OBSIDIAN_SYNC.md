---
type: Runbook
title: "CouchDB Obsidian Sync"
description: "Deployment, connection details, verification commands, and recovery notes for the Pi5 CouchDB backend"
timestamp: 2026-09-14T00:00:00Z
---

# CouchDB Obsidian Sync

## Purpose

CouchDB runs on the Raspberry Pi 5 datastore node as the sync backend for this
Obsidian vault and as a small general document datastore. It is deployed as a
portless Docker service behind the VPS Traefik -> Rathole -> Orange Pi Traefik
edge path.

## Deployment

| Item | Value |
| ---- | ----- |
| Host | Raspberry Pi 5 gateway |
| Stack path | `/ssd-data/infra` |
| Container | `couchdb` |
| Image | `couchdb:3.3.3` |
| Docker network | `proxy_net` |
| Host port exposure | None |
| Internal port | `5984` |
| Data volume | `/ssd-data/infra/couchdb/data` |
| Local config | `/ssd-data/infra/couchdb/local.d/obsidian.ini` |

## Public Endpoints

| Endpoint | Purpose |
| -------- | ------- |
| `https://couchdb.dungxbuif.com` | Primary CouchDB endpoint |
| `https://sync-db.dungxbuif.com` | Alias endpoint for sync clients |

Both endpoints are routed:

```text
Internet
-> Cloud VPS gateway-traefik HostSNI allow-list
-> Rathole tunnel
-> Orange Pi edge_traefik
-> couchdb:5984 over homelab-net/proxy_net
```

## Obsidian Client Settings

Use a dedicated non-admin sync user.

| Setting | Value |
| ------- | ----- |
| Remote database URI | `https://couchdb.dungxbuif.com` |
| Database name | `obsidian_vault` |
| Username | `obsidian_sync` |
| Password source | `/ssd-data/infra/couchdb/obsidian-sync.env` on the Pi |

Do not store the password directly in vault notes.

## Credentials

Credential files on the Pi:

```text
/ssd-data/infra/couchdb/.env
/ssd-data/infra/couchdb/obsidian-sync.env
```

- `.env` contains the CouchDB admin bootstrap credentials and CouchDB secrets.
- `obsidian-sync.env` contains the non-admin Obsidian sync user and database settings.
- Both files should remain `0600` and must not be committed.
- Local operational reference: `local_vars.json` -> `COUCHDB_SECRETS`
  contains the current CouchDB admin, sync user, endpoint, and database names.

## Database Layout

| Database | Purpose |
| -------- | ------- |
| `_users` | CouchDB user documents |
| `_replicator` | CouchDB replication metadata |
| `_global_changes` | CouchDB global changes metadata |
| `obsidian_vault` | Main Obsidian sync database |
| `homelab` | General homelab CouchDB database, created 2026-09-14; empty at creation (`doc_count=0`); keep app-specific `_security` unset until a consuming service is assigned |

The `obsidian_vault` database is restricted with `_security`:

- Admin: CouchDB admin user.
- Member: `obsidian_sync` user and `obsidian_sync` role.
- Anonymous access should return `401`.

Current non-admin user document:

- `org.couchdb.user:obsidian_sync`

The `homelab` database currently relies on CouchDB's global authenticated-only
setting; anonymous access returned `401` after creation. Add explicit
`_security` before assigning it to a specific app.

## Verification

Run from the Pi gateway.

```bash
cd /ssd-data/infra
docker ps --filter name=couchdb
docker logs --tail 80 couchdb
```

Since 2026-10-20 `couchdb.dungxbuif.com` is LAN-only (`lan-only` middleware) and
`sync-db.dungxbuif.com` is the Internet endpoint for LiveSync, limited to `/`,
`/_session` and `/obsidian_vault…`. Configure the plugin with the `sync-db` host.

Test public path through the VPS gateway:

```bash
curl -k --resolve sync-db.dungxbuif.com:443:103.82.21.202 \
  -u "$COUCHDB_SYNC_USER:$COUCHDB_SYNC_PASSWORD" \
  https://sync-db.dungxbuif.com/obsidian_vault
```

Expected:

- Authenticated sync user receives `200`.
- Anonymous request receives `401`.
- CORS preflight from `app://obsidian.md` receives `204`.
- `homelab` exists and returns metadata with `doc_count=0` when queried as the
  CouchDB admin.

## Headless Local LiveSync CLI

The optional local headless client uses the upstream Self-hosted LiveSync CLI.
CouchLoom on VM100 uses the vendored LiveSync common library directly against
this CouchDB database and does not run a second CLI sync node. The local
runner and state layout are documented in
[`couchloom/docs/LOCAL_LIVESYNC.md`](../../couchloom/docs/LOCAL_LIVESYNC.md).

Run the checks from the CouchLoom checkout:

```bash
tools/livesync/livesync.sh doctor
tools/livesync/livesync.sh remote-status
tools/livesync/livesync.sh sync
```

The runner stores its settings and PouchDB state outside Git with mode `0600`
settings. It reads the sync credentials from the existing homelab
`local_vars.json` unless explicit `LIVESYNC_*` variables are supplied.

If LiveSync reports that the remote database is locked and this device is not
accepted, stop. Do not use `unlock-remote` from an empty or unverified local
database. Complete the rebuild on the existing trusted Obsidian device first,
then retry the commands above. Only after a successful sync and mirror pass
should a persistent daemon be enabled.

## CORS

Configured in:

```text
/ssd-data/infra/couchdb/local.d/obsidian.ini
```

Allowed origins currently include:

- `app://obsidian.md`
- `capacitor://localhost`
- `http://localhost`
- `http://127.0.0.1`
- `https://couchdb.dungxbuif.com`

## Gateway Configuration

Pi Caddy route:

```caddy
@couchdb host couchdb.dungxbuif.com sync-db.dungxbuif.com
handle @couchdb {
    reverse_proxy couchdb:5984
}
```

Cloud VPS Nginx whitelist includes:

```nginx
sync-db.dungxbuif.com rathole-server:443;
couchdb.dungxbuif.com rathole-server:443;
```

## Recovery Notes

If CouchDB is down:

```bash
cd /ssd-data/infra
docker compose up -d couchdb
docker logs --tail 120 couchdb
```

If Caddy route is changed:

```bash
cd /ssd-data/infra
docker compose exec -T caddy caddy reload --config /etc/caddy/Caddyfile
```

If VPS whitelist is changed:

```bash
cd /root/gateway
docker compose exec -T nginx-gateway nginx -t
docker compose restart nginx-gateway
```

## Related

- [Raspberry Pi 5 Datastore Spec](./PI.md)
- [Directory Update Log](./LOG.md)
- [System Context & Playbook](./MAIN.md)
