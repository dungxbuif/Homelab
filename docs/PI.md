---
type: Reference
title: "Raspberry Pi 5 Datastore Specification"
description: "Technical specification of the Pi5 manager/datastore node: PostgreSQL, Redis, object storage, and persistent services"
timestamp: 2026-10-13T00:00:00+07:00
---

# System Specification & Architectural Design: Pi5 Datastore Infrastructure

> **Host Device:** Raspberry Pi 5 (ARM64 Architecture - Broadcom BCM2712) **Host Static LAN IP:** `10.10.0.5` **Target Audience:** AI Coding & DevOps Agents **Root Directory:** `/ssd-data` (High-speed External SSD mounted on Raspberry Pi 5) **Role:** Docker Swarm manager, active Traefik/Rathole/AdGuard edge, datastore, and persistent-services host.

> **Current runtime source:** [Runtime Inventory and Deployment Reconciliation](./deployments/runtime-inventory-2026-10-13.md). This file contains the Pi5 architecture and runbook; the linked audit contains current image IDs, replica state, and backup markers.

This workspace houses the complete configuration, provisioning scripts, security policies, and orchestration definitions for the **Home Gateway Infrastructure** running as a self-hosted single-board server on a **Raspberry Pi 5**. The entire infrastructure state is stored on a high-speed external SSD mounted at `/ssd-data`.

---

## 🗺️ Workspace Directory Map

```text
/ssd-data
├── index.md               # Unified gateway, network topology, and agent instructions
├── .gitignore             # Multi-tier exclusion list for repository security, logs, and docker volumes
├── backup/                # Gitignored directory containing historical system backups
├── rathole-build/         # Build context for compiling/testing local Rathole binaries
└── infra/                 # Operational runtime stack directory
    ├── docker-compose.yml # Main Docker Compose orchestration file defining all gateway microservices
    ├── README.md          # Human-oriented vietnamese system catalog and maintenance runbooks
    ├── kuma-data/         # Inactive configs for Uptime Kuma monitoring (decommissioned)
    ├── my-cv/             # Static volume path for custom CV web application
    ├── postgres/          # Centralized PostgreSQL database storage
    │   └── data/          # Persistent database files
    ├── netdata/           # System resources monitoring configuration profiles
    ├── registry/          # Dynamic volumes and security credentials for local Docker Registry
    │   └── auth/          # Htpasswd credentials for docker login authentication
    ├── redis-prod/        # Standalone Redis for macocr-proxy and approved services
    │   └── docker-compose.yml  # bind 10.10.0.5:16379, auth, AOF (see Redis-Prod section)
    └── rustfs/            # High-performance S3 object storage directories (RustFS engine backend)
```

---

## 📐 System Architecture & Service Connections

Pi5 supplies datastore and HTTP backend services to VM100 over the attachable
`homelab-net` Swarm overlay and is also the active home edge. The normal public
path is VPS `gateway-traefik` -> shared Rathole -> Pi5 standalone
`edge-traefik-pi5`. Pi5 `edge-adguardhome-pi5` resolves active split-horizon
names to the Pi5 edge on the LAN. The old Orange Pi edge is down and the old
Swarm edge services are scaled to zero.

---

## 🔒 Portless Security & Ingress Invariants

### 1. Controlled Host Port Exposure

Pi5 core services remain portless unless an inventoried exception requires
LAN access. PostgreSQL remains unchanged: the raw container is internal and
PgBouncer continues to provide the existing `10.10.0.5:5432` client endpoint.
The VM100 n8n, Family Tree, OCR proxy, and MyPocket services use the equivalent
private overlay endpoint `pgbouncer:6432`; GitLab alone uses direct
`postgres:5432` because the current pooler is session-mode. The LAN mapping remains for clients
that have not migrated.
Redis-prod remains the other documented LAN datastore endpoint on `:16379`.
RelayHub application compute was moved to VM100; the old Pi5 RelayHub
API/worker/NATS containers are stopped and only the RelayHub PostgreSQL
container remains healthy for datastore duty. The 2026-09-15 audit also found
monitoring `alertmanager:9093`/`victoriametrics:8428` host binds. Both are now
LAN-bound at `10.10.0.5:9093` and `10.10.0.5:8428`. See the
[network audit](./research/network-segmentation-2026-09-15.md) and
[resource inventory](./research/resource-limit-audit-2026-09-15.md).

- **PostgreSQL (`postgres`)** does not declare `ports`. A host scan **does**
  see Pi5 `:5432` open because PgBouncer publishes that port; it does not
  expose the raw PostgreSQL container.
- **RustFS S3 (`rustfs`)** does not expose ports `9000` or `9001` directly to the host. External S3 client requests are securely routed via subdomains: S3 API via `storage.dungxbuif.com` and S3 Console via `cdn.dungxbuif.com`.

### 2. Edge Routing Boundary

TLS and route ownership live on the Pi5 standalone Traefik. The canonical
router and service definitions are in [`../migration/traefik/dynamic.yml`](../migration/traefik/dynamic.yml).
Pi5-backed routes currently include:

- Dynamic subdomain mapping routes requests as follows:
    - `cdn.dungxbuif.com` →→ proxied internally to `rustfs:9001` (S3 Web Console)
    - `storage.dungxbuif.com` →→ proxied internally to `rustfs:9000` (S3 API)
    - `registry.dungxbuif.com` →→ proxied internally to `registry:5000` (Private Docker Registry)
    - `speed.dungxbuif.com` →→ proxied internally to `librespeed:80`
    - `pgadmin.dungxbuif.com` →→ proxied internally to `pgadmin:80`
    - `couchdb.dungxbuif.com` and `sync-db.dungxbuif.com` -> `couchdb:5984`

n8n is no longer a Pi5-hosted edge route; it now runs on VM100 and uses Pi5
PostgreSQL database `n8n` through the private `pgbouncer:6432` overlay
endpoint (changed from the equivalent LAN PgBouncer mapping on 2026-09-15).
RelayHub is likewise no longer a Pi5-hosted app; VM100 runs API/worker/NATS/Redis,
while Pi5 keeps only PostgreSQL database `relayhub`.
GitLab runs on VM100 and its public HTTPS/SSH routes are live through isolated
VPS tunnels; no Orange Pi GitLab route is active. Grafana
remains retired. See [GitLab service runbook](./services/gitlab.md) for the
temporary route and rollback.
PostgreSQL is not an edge route and must not be added to the Traefik dynamic
configuration.

---

## 🎛️ Network, Container & Technical Parameters Blueprint

Below is the core datastore/HTTP mapping for Pi5. It is not a complete
container inventory; telemetry and RelayHub development containers are
listed in the [resource audit](./research/resource-limit-audit-2026-09-15.md).

### 1. Container Allocation & Service Matrix

|Service|Container Name|Docker Image & Version|Port Mapping (Host / Container)|Subdomain Routing / Ingress Target|Core Purpose & Technical Parameters|
|---|---|---|---|---|---|
|**RustFS Storage**|`rustfs`|`rustfs/rustfs:1.0.1`|**Portless** on `proxy_net` and `homelab-net`|`storage.dungxbuif.com` (S3 API) <br>`cdn.dungxbuif.com` (Console)|ARM64 S3 storage; ports 9000/9001 internal.|
|**Private Registry**|`docker-registry`|`registry:2`|**Portless** on `proxy_net` and `homelab-net`|`registry.dungxbuif.com`|Docker image registry on Pi5 SSD.|
|**Librespeed**|`librespeed`|`lscr.io/linuxserver/librespeed`|**Portless** on `proxy_net` and `homelab-net`|`speed.dungxbuif.com`|LAN/WAN speedtest backend.|
|**Centralized PostgreSQL**|`postgres`|`pgvector/pgvector:pg16`|**Portless** on `proxy_net` and `homelab-net`; PgBouncer maps LAN `:5432` to pooler `:6432`|Direct container DNS `postgres:5432` only for approved clients such as GitLab; LAN `10.10.0.5:5432` is PgBouncer, not raw PostgreSQL; no edge route|Pinned backend DB serving Pi5 apps and approved VM100 services.|
|**pgAdmin 4**|`pgadmin`|`dpage/pgadmin4:latest`|**Portless** on `proxy_net` and `homelab-net`|`pgadmin.dungxbuif.com`|PostgreSQL administration UI.|
|**CouchDB**|`couchdb`|`couchdb:3.3.3`|**Portless** on `proxy_net` and `homelab-net`|`couchdb.dungxbuif.com` <br>`sync-db.dungxbuif.com`|Obsidian sync and document databases.|

The retired `my-cv` container is not part of the running Pi5 inventory.
The Pi5 `docker-registry` is still the production image registry. GitLab's
separate VM100 bundled Registry trial at `registry-gitlab.dungxbuif.com`
does not replace this container or its Pi5 SSD storage; native lab
Docker/Swarm pulls are not yet verified for the trial domain. See
[GitLab Registry trial](./deployments/gitlab-registry-trial-2026-09-16.md).
Public `dungxbuif.com` is served by VM100 Swarm `tasks.homepage:80` through
the active Pi5 Traefik; the old VM100 Compose `:18081` path is stopped rollback.

---

## 🔑 Docker Registry Credentials & Shared CI/CD Spec

- **Domain Endpoint**: `https://registry.dungxbuif.com`
- **Authentication Engine**: HTTP Basic Authentication via Htpasswd (`/ssd-data/infra/registry/auth/htpasswd`)
- **Active Service User**: **`dungxbuif`**
- **Password Encryption**: Apache Bcrypt (`$2y$`)
- **Local Secret Reference**: `local_vars.json` $\rightarrow$ `LEGACY_SYSTEM_SECRETS.REGISTRY_USER` / `REGISTRY_PASSWORD`
- **Client login:** use the registry credentials from `local_vars.json`; do not
  duplicate them in repository files.

---

## 📂 Volume Allocation & Container Management Invariants

To keep the home lab on the Raspberry Pi 5 clean, easy to backup, and immune to volume conflicts or permission issues, all service configurations must adhere strictly to these three rules:

### Rule 1: Centralized Architecture (Single Infrastructure Stack)

- Every single microservice container in the Home Lab stack must be declared inside the centralized Docker Compose file: `/ssd-data/infra/docker-compose.yml`.
- **DO NOT** spread compose files or standalone docker containers across disparate host folders. Stacking them together makes backup operations as simple as taking a snapshot of the `/ssd-data/infra` directory.

### Rule 2: Service-Named Volume Folders (Volume Folder Convention)

All bind mounts mapped from the host filesystem into container layers must declare relative paths and group neatly under service-named subfolders `./<service-name>/...`:

1. **Static Files & Configuration Files (Static Config):** Mount single config files directly or group configurations in `./<service-name>/config` or `./<service-name>/auth`.
2. **Dynamic Volumes & Databases (Dynamic Data):** Group files inside `./<service-name>/data` or `./<service-name>/db_storage`.
    - _Examples:_
        - RustFS: `./rustfs:/data` (S3 object storage files live cleanly inside `./rustfs`)
        - PostgreSQL Central: `./postgres/data:/var/lib/postgresql/data`

### Rule 3: Smart Centralized Backup
**Status (2026-09-13): existing directory-upload job, owner-confirmed.** The
current mechanism uploads a whole directory to Google Drive. Its database-aware
coverage, consistency, schedule and restore behavior have not been verified.
The earlier assessment that no backup solution existed was incorrect: the gap
is reliable multi-engine database backup, not the absence of Drive uploads.
Pi5 should remain a dedicated datastore; backup orchestration belongs on VM100.

See [Google Drive database backup proposal](./research/google-drive-db-backup-2026-09-13.md)
for the proposed replacement. It is not deployed.

#### Historical Backup Description (Unverified)
The previous documentation claimed the following automated strategy:
*   **Tools:** `rclone` (Google Drive Integration) + `zip` + `pg_dump`.
*   **Strategy:**
    *   **PostgreSQL:** Automated daily `.sql` dumps prior to compression to ensure complete database transactional integrity.
    *   **Ingress & Application Data:** Backs up all critical configuration and persistent asset folders inside `/ssd-data/infra` (excluding temporary caches, runtime log files, and netdata profiles).
    *   **Frequency:** Every day at 01:00 AM local time.
*   **Retention Policy:** Retains backups locally for 7 days (stored under `/tmp/backups`) and remotely on Google Drive for 30 days (stored under `server-backups` directory).

### Current backup implementation (2026-10-13)

The whole-directory upload description above is historical and is not the
current recovery contract. The active implementation keeps Pi5 as the online
datastore/RustFS host and exports PostgreSQL/CouchDB logically, RustFS through
S3, and GitLab through its native VM100 workflow. A complete local database
run and isolated restore rehearsal are recorded in
[the 2026-10-05 evidence note](./deployments/backup-restore-rehearsal-2026-10-05.md).
VM100 systemd timers now own the schedule and Pi5 remains the online
datastore/object executor. The latest database, RustFS, and GitLab success
markers plus remote snapshot IDs are in the [runtime inventory](./deployments/runtime-inventory-2026-10-13.md).
Redis and NATS remain excluded. The combined Semaphore health check passed as
task 57 on 2026-10-15 with free space, lock state, and all three class markers
within policy; remote Drive restore remains a separate acceptance gate.

---

## 🪵 Key Troubleshooting Registry & Decisions

1. **Current AdGuard placement (2026-10-13):** DNS runs as the standalone
   `edge-adguardhome-pi5` container on Pi5 `10.10.0.5`. The old Orange Pi
   `edge_adguardhome` service is `0/0` and must not be restored implicitly.

---

## 🗄️ Database Management
All system databases are centrally hosted within the `postgres` container (fronted by PgBouncer on `:5432`) on the Raspberry Pi 5, and shared by approved Pi5, VM100, and Mac dependency workloads.
Legacy K8s-era database history (not a current inventory):
[archived/k8s-v2/k8s/DB_INVENTORY.md](./archived/k8s-v2/k8s/DB_INVENTORY.md).

GitLab CE 18.11.11 has its own `gitlabhq_production` database and `gitlab`
owner role in this same PostgreSQL instance. Extensions `amcheck`,
`btree_gist`, `pg_trgm`, and `plpgsql` are installed. Its Swarm service on
VM100 connects privately to `postgres:5432`; DB credentials are a Swarm
secret, not stored in this document. Pi5 PostgreSQL remains capped at
2 GiB/1.5 CPU. See [GitLab service runbook](./services/gitlab.md).

### Batdongsan database migration

On 2026-09-13, the Batdongsan production database was restored from the VPS
snapshot into the Pi5 central PostgreSQL service:

- Database: `bds_prod`
- Role: `bds_user`
- Verified data: `listings=31`, `users=4`
- Backup source retained on VPS: `/root/backup-bds/bds_prod_snapshot_20260913_121113.sql`
- Snapshot SHA256: `9baa9613153312519e005c72ffc5b8237a2adbdf40e682cb8ba17708fcaf692e`

For container-only access, both `postgres` and `pgbouncer` are attached to the
attachable Swarm overlay `homelab-net`:

```text
build-time:  postgres:5432
runtime:     pgbouncer:6432
```

Do not expose this database through Cloudflare Tunnel or host ports. BDS app
uses Docker DNS on `homelab-net` for database access. The Cloudflare Tunnel
container is isolated on VM100's `bds-tunnel-net` bridge and reaches only
`bds-app:3000`; it must not join `homelab-net`.

### NetBird databases

On 2026-09-13, the VM100 NetBird bootstrap was moved from its initial SQLite
volume to Pi5 PostgreSQL:

- Role: `netbird`
- Databases: `netbird`, `netbird_activity`, `netbird_idp`
- Access path: `pgbouncer:6432` over `homelab-net`
- Verified schema counts: `39`, `2`, and `13` public tables respectively

NetBird still runs on VM100 as Swarm services. Pi5 stores the data only and
must not run the NetBird dashboard or management server.

---

## ⚡ Redis-Prod (v3 NEW)

A **standalone** Redis instance was added on the Pi5 to back approved production
workloads (macocr-proxy queue and approved service state). It is intentionally **not** part of
the centralized `docker-compose.yml` because it binds a host port for LAN
access from the Mac:

| | |
---|---|
Compose | `/ssd-data/infra/redis-prod/docker-compose.yml` |
Image | `redis:7.2-alpine` (pinned, arm64) |
Bind | `10.10.0.5:16379` (uncommon port — avoids dev `6379` clashes) |
Auth | password (`requirepass`) — see `local_vars.json` |
Persistence | AOF (`appendonly yes`) |
Memory | `maxmemory 1gb`, `noeviction` (writes fail at cap instead of evicting keys) |

> [!NOTE]
> This is a **deliberate exception** to the portless principle: approved LAN
> clients reach Redis over LAN at `10.10.0.5:16379`; Swarm clients use the
> `redis-prod:6379` alias on `homelab-net`. It is the only Pi5 datastore
> with a documented Pi5 host-port bind, alongside PgBouncer's LAN `:5432`.

Pi5 has a 4 GiB NVMe-backed swapfile at `/ssd-data/infra/swapfile`, enabled by
`homelab-pi5-swap.service` with `vm.swappiness=10`. Swap is an OOM buffer, not
additional physical RAM. See [resource audit](./research/resource-limit-audit-2026-09-15.md).


1. **NEVER expose new host ports** in the `docker-compose.yml` unless explicitly requested. All new services must remain isolated inside the virtual virtual network `proxy_net`.
2. **NEVER use the generic `latest` tag** for system images in compose files. Pin down exact tags (e.g., `rustfs/rustfs:1.0.0-beta.3`, `postgres:16`) to guarantee runtime consistency and predictability.
3. **DO NOT run invasive host-level commands** with `sudo` if they prompt for password inputs. Leverage helper container volume mounts to modify files with root/non-root UID restrictions.
4. **ALWAYS keep verification scripts updated** inside `/ssd-data/scratch/` whenever security rules or credentials change to ensure CI/CD workflows and automatic verification procedures continue to pass cleanly.
5. **MANDATE ARM64 Compatibility:** Because this home lab runs on a single-board **Raspberry Pi 5 (ARM64 architecture)**, any new docker image or backend library added to compose must explicitly support the `linux/arm64` platform target. All compiled binaries inside `rathole-build` must target ARM instruction sets.
