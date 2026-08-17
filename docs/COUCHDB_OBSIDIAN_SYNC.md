---
type: Runbook
title: "CouchDB Obsidian Sync"
description: "Deployment, connection details, verification commands, and recovery notes for the CouchDB backend used by Obsidian vault sync"
timestamp: 2026-07-08T00:00:00Z
---

# CouchDB Obsidian Sync

## Purpose

CouchDB runs on the Raspberry Pi 5 gateway as the sync backend for this Obsidian vault. It is deployed as a portless Docker service behind Caddy and the Cloud VPS Nginx gateway.

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
-> Cloud VPS Nginx whitelist
-> Rathole tunnel
-> Raspberry Pi Caddy
-> couchdb:5984 inside proxy_net
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

## Database Layout

| Database | Purpose |
| -------- | ------- |
| `_users` | CouchDB user documents |
| `_replicator` | CouchDB replication metadata |
| `_global_changes` | CouchDB global changes metadata |
| `obsidian_vault` | Main Obsidian sync database |

The `obsidian_vault` database is restricted with `_security`:

- Admin: CouchDB admin user.
- Member: `obsidian_sync` user and `obsidian_sync` role.
- Anonymous access should return `401`.

## Verification

Run from the Pi gateway.

```bash
cd /ssd-data/infra
docker ps --filter name=couchdb
docker logs --tail 80 couchdb
```

Test public path through the VPS gateway:

```bash
curl -k --resolve couchdb.dungxbuif.com:443:103.82.21.202 \
  -u "$COUCHDB_SYNC_USER:$COUCHDB_SYNC_PASSWORD" \
  https://couchdb.dungxbuif.com/obsidian_vault
```

Expected:

- Authenticated sync user receives `200`.
- Anonymous request receives `401`.
- CORS preflight from `app://obsidian.md` receives `204`.

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

- [Raspberry Pi 5 Gateway Spec](./PI.md)
- [Directory Update Log](./LOG.md)
- [System Context & Playbook](./MAIN.md)
