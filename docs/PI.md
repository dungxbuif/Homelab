---
type: Reference
title: "Raspberry Pi 5 Datastore and Edge Host"
description: "Current state of the Pi5 Swarm manager: datastores, edge, ports, storage paths, operations and rollback"
timestamp: 2026-10-31T00:00:00+07:00
---

# Raspberry Pi 5 — Swarm manager, datastore and edge

Source: live read-only audit 2026-10-31 plus the
[2026-10-31 upgrade ledger](./deployments/version-upgrade-2026-10-31.md).
Forward plan: [Lab IaC automation rebuild](./superpowers/plans/2026-10-31-lab-iac-automation-rebuild.md).

## Role and specs

| Field | Value |
|---|---|
| Hardware | Raspberry Pi 5, ARM64 (BCM2712); every image must support `linux/arm64` |
| Hostname / LAN IP | `rpivn` / `10.10.0.5` (SSH alias `pi`) |
| Role | Docker Swarm manager/leader, authoritative datastore, home edge (Traefik, Rathole client, AdGuard DNS), private image registry |
| Docker | 28.4.0 |
| Storage | External NVMe SSD at `/ssd-data`; root `/` 469 G, 42 % used |
| Swap | 4 GiB `/ssd-data/infra/swapfile` via `homelab-pi5-swap.service`, `vm.swappiness=10` (unverified) |
| systemd | No homelab timers. Native units: `cloudflared` (degraded, see below), `databasus-verification-agent.service` |

Pi5 stays the data host. VM100 is application compute; VM110 (`db-ops`) runs
db-management. Moving data off Pi5 requires a separate failure-domain target
and a restore drill first.

## Swarm cluster (managed from Pi5)

Nodes: `rpivn` (leader), `vm100-prod`, `db-ops` (VM110), and `orangepizero3`
which is **down but still a member** — remove it deliberately, do not schedule
onto it. Leftover `0/0` services: `edge_traefik`, `edge_rathole`,
`edge_adguardhome`, `relayhub` (legacy bootstrap), `mypocket-web`. Do not scale
these up implicitly; the edge now runs as standalone containers on Pi5.

All Swarm service state (including VM100/VM110 tasks) is inspected and updated
from Pi5: `docker service ls`, `docker service ps <svc>`. Semaphore and
`homelab-provisioner` run as Swarm services on the Pi5 control plane
(placement unverified).

## What runs on Pi5 outside Swarm

| Unit | Runtime | Image / version | Notes |
|---|---|---|---|
| `postgres` | Compose `infra` | `pgvector/pgvector:pg16@sha256:7b822b0a…` (PostgreSQL 16.15) | No host port; on `pg-net`, `proxy_net`; cap 2 GiB / 1.5 CPU (unverified) |
| `pgbouncer` | Compose `infra` | `edoburu/pgbouncer:latest@sha256:ca2814bc…` (1.26.1) | LAN `10.10.0.5:5432` → pooler `:6432`; overlay alias `pgbouncer:6432` |
| `couchdb` | Compose `infra` | `couchdb:3.5.3@sha256:bed314d1…` | Obsidian LiveSync source of truth; routes `couchdb.` / `sync-db.dungxbuif.com` |
| `couchdb-backup-proxy` | Compose `infra` | — | GET/HEAD-only, LAN `10.10.0.5:15984`, VM100 source only |
| `rustfs` | Compose `infra` | `rustfs/rustfs:1.0.4@sha256:ed9210d6…` | S3 API `storage.dungxbuif.com` (`:9000`), console `cdn.dungxbuif.com` (`:9001`); no host port; on `s3-net` |
| `victoriametrics` | Compose `infra` | `v1.155.0` | LAN `10.10.0.5:8428` |
| `alertmanager` | Compose `infra` | `v0.34.2` | LAN `10.10.0.5:9093` |
| exporters, `cadvisor` | Compose `infra` | postgres-exporter v0.18.1, blackbox, snmp, cAdvisor v0.55.1 | Scrape targets only |
| `redis-prod` | Compose `redis-prod` | `redis:7.2-alpine@sha256:2c933526…` (7.2.17) | See Redis below |
| `edge-traefik-pi5` | standalone | `traefik:v3.6` | Ports 80/443; all lab TLS/route ownership |
| `edge-rathole-pi5` | standalone | `rathole:local` (hand-built) | Client to the VPS shared Rathole server |
| `edge-adguardhome-pi5` | standalone | `adguard/adguardhome:latest` | LAN DNS, split-horizon to the Pi5 edge |
| `docker-registry` | standalone | `registry:2` | Production registry `registry.dungxbuif.com`; htpasswd auth |

Floating tags still in use: AdGuard `latest`, PgBouncer `latest`, blackbox/SNMP
exporters, `registry:2`, `rathole:local`. Pin before automating.

## Storage paths

```text
/ssd-data/infra/docker-compose.yml        # `infra` Compose source (contains credentials; never copy)
/ssd-data/infra/postgres/data             # PostgreSQL data
/ssd-data/infra/rustfs                    # RustFS object data
/ssd-data/infra/registry/                 # registry data; auth/htpasswd (bcrypt)
/ssd-data/infra/redis-prod/               # docker-compose.yml + docker-compose.override.yml, data/ (AOF)
/ssd-data/infra/gitlab/{deploy,secrets}   # GitLab stack deploy dir and mode-0600 secret sources
/ssd-data/infra/backup/secrets/rclone.conf
/ssd-data/infra/services/databasus-verification/
/ssd-data/infra/backups/version-upgrade-20261031/   # pre-upgrade archives, specs, rollback sources
```

Edge route source of truth: `homelab-ops/migration/traefik/dynamic.yml`
(the generated `routes/` output is not live yet).

## Networking and ports

Public path: VPS `gateway-traefik` (HostSNI) → VPS Rathole → `edge-rathole-pi5`
→ `edge-traefik-pi5` → service (VM100 services via `tasks.<service>` DNSRR).
Overlays used by Pi5 datastores: `pg-net`, `s3-net`, `homelab-net`,
`gitlab-net`, `edge-http-net`, `data-net`.

Host-port exceptions (everything else is portless):

| Bind | Service | Consumers |
|---|---|---|
| `:80`, `:443` | edge Traefik | Rathole / LAN clients |
| `:53` | AdGuard | LAN DNS (unverified bind) |
| `10.10.0.5:5432` | PgBouncer (not raw PostgreSQL) | LAN clients not yet on overlay |
| `10.10.0.5:16379` | redis-prod | Mac / LAN clients |
| `10.10.0.5:15984` | couchdb-backup-proxy | VM100 backup relay only |
| `10.10.0.5:8428`, `:9093` | VictoriaMetrics, Alertmanager | LAN |

PostgreSQL must never get an edge route or a public port. GitLab is the only
client using direct `postgres:5432` (session-mode pooler); everything else uses
`pgbouncer:6432`.

## Datastore contents

- **PostgreSQL** (17 databases at the 2026-10-31 dump): includes `n8n`,
  `homelab`, `relayhub` (legacy Go, rollback only),
  `relayhub_v1_staging_20261030` (live RelayHub v1), `netbird`,
  `netbird_activity`, `netbird_idp`, `gitlabhq_production` (owner `gitlab`;
  extensions `amcheck`, `btree_gist`, `pg_trgm`), `family_tree`, `macocr`,
  `mypocket`, `whiteboard`, `bds_prod` (app retired, data retained), and
  retired `goclaw`/`omniscan`. Inventory query:
  `docker exec postgres psql -U admin -d postgres -Atc "SELECT datname FROM pg_database WHERE NOT datistemplate"`.
- **Redis-prod**: AOF on, `maxmemory 1gb`, `noeviction`, `requirepass`.
  DB 0 macocr-proxy, DB 1 MyPocket, DB 2 GitLab. Swarm clients use
  `redis-prod:6379` on `homelab-net`/`gitlab-net`. Always run Compose with
  **both** the base and override files — base-only recreate drops the
  `gitlab-net` attachment. See [GitLab ↔ Redis runbook](./runbooks/gitlab-redis-network.md).
- **Registry**: user `dungxbuif`; credentials in `local_vars.json`
  (`LEGACY_SYSTEM_SECRETS.REGISTRY_USER` / `REGISTRY_PASSWORD`) and 1Password.

## Known issues

- `cloudflared` (native systemd 2026.10.7) loops in `activating/auto-restart`:
  the token returns `Unauthorized: Tunnel not found`. Needs the Cloudflare
  owner to reissue the tunnel; no live route depends on it. Old binary SHA-256
  for rollback: `03c5d58e…`; artifacts in the backup dir above.
- Stale Docker networks remain (`bds-app_bds_network`, `datcom_default`,
  `dungxbuif_default`, `traefik_proxy`, `relayhub_relayhub`, …).
- Databasus verification agent needs Docker access; `userns-remap` is disabled.

## Operations

- Change one service at a time: back up source + data, apply, smoke, record
  rollback. Never use `latest` in new Compose entries; no new host ports
  without an explicit request.
- Backups: Databasus (Pi5 PostgreSQL jobs, verified restores for the six
  approved service DBs) and the db-management stack on VM110. See
  [backup runbook](./runbooks/backup-restore.md) and
  [Databasus operations](./runbooks/databasus-backup-operations.md).

## Rollback (current upgrade set)

Pre-upgrade archives, Compose sources and service specs for every 2026-10-31
change are under `/ssd-data/infra/backups/version-upgrade-20261031/<service>/`;
previous images remain in the local image cache. For a stateful service: stop
it, restore the previous image reference in the Compose source, start it, and
restore its archive only if data is incompatible. PgBouncer's previous
container is retained as `pgbouncer-rollback-version-upgrade` (image tag
`edoburu/pgbouncer:rollback-version-upgrade`). Never delete or recreate a data
volume as a first response.
