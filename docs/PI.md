---
type: Reference
title: "Raspberry Pi 5 Gateway Specification"
description: "Technical specification of the Home Ingress Pi 5 (v3): Caddy TLS edge, Rathole client, AdGuard DNS, Postgres+Redis datastores, and the portless Docker stack"
timestamp: 2026-08-17T00:00:00Z
---

# System Specification & Architectural Design: Home Gateway Infrastructure

> **Host Device:** Raspberry Pi 5 (ARM64 Architecture - Broadcom BCM2712) **Host Static LAN IP:** `<PI_IP>` (Local LAN Network) **Target Audience:** AI Coding & DevOps Agents **Root Directory:** `/ssd-data` (High-speed External SSD mounted on Raspberry Pi 5) **Core Design Principles:** Zero Host Port Exposure (Portless Design), Unified Reverse Proxy Ingress, Strict Custom S3 IAM Policies, ARM64 Hardware Optimization, Zero Sudo dependency for standard tasks.

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
    ├── Caddyfile          # Ingress routing rules & dynamic wildcard TLS config via Cloudflare DNS-01
    ├── README.md          # Human-oriented vietnamese system catalog and maintenance runbooks
    ├── adguard/           # persistent work folders and DNS configurations for AdGuard Home
    ├── caddy/             # Persistent ACME certificates storage and Caddy dynamic configurations
    ├── kuma-data/         # Inactive configs for Uptime Kuma monitoring (decommissioned)
    ├── my-cv/             # Static volume path for custom CV web application
    ├── n8n/               # persistent workflow configurations
    │   └── n8n_storage/   # Dynamic n8n assets & custom runtime integrations
    ├── postgres/          # Centralized PostgreSQL database storage
    │   └── data/          # Persistent database files
    ├── netdata/           # System resources monitoring configuration profiles
    ├── rathole/           # Configuration files for Rathole client NAT traversal tunnels
    ├── registry/          # Dynamic volumes and security credentials for local Docker Registry
    │   └── auth/          # Htpasswd credentials for docker login authentication
    ├── redis-prod/        # [v3 NEW] Standalone Redis for Mac omniscan-bot/macocr-proxy
    │   └── docker-compose.yml  # bind 0.0.0.0:16379, auth, AOF (see Redis-Prod section)
    └── rustfs/            # High-performance S3 object storage directories (RustFS engine backend)
```

---

## 📐 System Architecture & Service Connections

The gateway infrastructure operates on an **Ingress-Proxy-Isolated** topology combined with NAT Traversal to expose localized services from inside a home lab to the public internet securely, utilizing a middleman VPS and local routing via Caddy.

The structural pivot of the reverse proxy **Caddy** is its **Hybrid Reverse Proxy Ingress** design: Caddy is configured to seamlessly route traffic directly into Docker-managed virtual subnets (`proxy_net`) using virtual domain mapping and simultaneously proxy traffic outward to **other physical nodes/servers in the local home lab using their static LAN IP addresses** (e.g. proxying `openclaw.dungxbuif.com` to a standalone machine at IP `<MIKROTIK_IP>2:18789`).

---

## 🔒 Portless Security & Ingress Invariants

### 1. Zero Host Port Exposure

Except for `caddy` (mapping ports `80` and `443` to host to handle HTTP/HTTPS ingress) and `adguardhome`/`rathole` (running in host network mode for direct low-level LAN DNS resolution and tunnel connectivity), **all other container services have no ports mapped to the host system**.

- **PostgreSQL (`postgres`)** does not declare the `ports` property. Unprivileged network scans of the host will _not_ detect port `5432` open.
- **RustFS S3 (`rustfs`)** does not expose ports `9000` or `9001` directly to the host. External S3 client requests are securely routed via subdomains: S3 API via `storage.dungxbuif.com` and S3 Console via `cdn.dungxbuif.com`.

### 2. TLS & Wildcard Ingress Strategy

Caddy serves as the secure cryptographic edge boundary. Armed with Cloudflare API tokens, it automatically negotiates wildcard certificates (`*.dungxbuif.com`) via the DNS-01 challenge. This eliminates standard HTTP port exposures and lets local hosts acquire trusted TLS certificates completely offline:

- Dynamic subdomain mapping routes requests as follows:
    - `cdn.dungxbuif.com` →→ proxied internally to `rustfs:9001` (S3 Web Console)
    - `storage.dungxbuif.com` →→ proxied internally to `rustfs:9000` (S3 API)
    - `registry.dungxbuif.com` →→ proxied internally to `registry:5000` (Private Docker Registry)
    - `speed.dungxbuif.com` →→ proxied internally to `librespeed:80`
    - `n8n.dungxbuif.com` →→ proxied internally to `n8n:5678`
    - `pgadmin.dungxbuif.com` →→ proxied internally to `pgadmin:80`
    - `dungxbuif.com` →→ proxied **over LAN** to the Mac mini (`10.10.0.10:18081`, homepage) [v3 — was Pi5 my-cv]
    - `ocr.dungxbuif.com` →→ proxied **over LAN** to the Mac mini (`10.10.0.10:18080`, macocr-proxy) [v3 — was K8s Traefik `10.10.0.30:80`]
    - `llm.dungxbuif.com` →→ proxied **over LAN** to the Mac mini (`10.10.0.10:1234`, LM Studio native)
    - `grafana.dungxbuif.com` →→ **retired** (404; was K8s, removed 2026-08)

---

## 🎛️ Network, Container & Technical Parameters Blueprint

Below is the exhaustive mapping table of services running on the Raspberry Pi 5 host machine (`<PI_IP>`):

### 1. Container Allocation & Service Matrix

|Service|Container Name|Docker Image & Version|Port Mapping (Host / Container)|Subdomain Routing / Ingress Target|Core Purpose & Technical Parameters|
|---|---|---|---|---|---|
|**Caddy Ingress**|`caddy`|`infra-caddy` (Custom build)|Host: `80:80`, `443:443`|Unified Ingress wildcard domain (`*.dungxbuif.com`)|Edge reverse proxy, routing ingress and dynamically managing TLS wildcard certs via CF DNS-01 API.|
|**Rathole Client**|`rathole`|`rathole:local` (Custom build)|Host Network Mode|Connected to VPS `<VPS_PUBLIC_IP>:7000`|NAT Traversal client forwarding public TCP 80/443 VPS traffic directly to local Caddy container at `127.0.0.1:80/443`.|
|**RustFS Storage**|`rustfs`|`rustfs/rustfs:1.0.0-beta.3`|**Portless** (Only within `proxy_net`)|`storage.dungxbuif.com` (S3 API)  <br>`cdn.dungxbuif.com` (Console)|High-performance ARM64 S3 Object Storage backend. Provides API (port 9000) and Web Console (port 9001).|
|**Private Registry**|`docker-registry`|`registry:2`|**Portless** (Only within `proxy_net`)|`registry.dungxbuif.com`|Docker Image Registry utilizing local SSD storage. Auth: Htpasswd (`dungxbuif` account, Bcrypt `$2y$`).|
|**Librespeed**|`librespeed`|`lscr.io/linuxserver/librespeed`|**Portless** (Only within `proxy_net`)|`speed.dungxbuif.com`|Lightweight localized speedtest engine for checking WAN and LAN transfer rates.|
|**AdGuard Home**|`adguardhome`|`adguard/adguardhome:latest`|Host Network Mode|N/A (DNS LAN Resolver)|Network-wide ad blocker and internal DNS resolver pointing domains to Caddy host.|
|**Centralized PostgreSQL**|`postgres`|`postgres:16`|**Portless** (Only within `proxy_net`) — fronted by PgBouncer on `:5432`|`postgres.dungxbuif.com:5432`|Pinned backend DB serving all services centrally: Pi5 `proxy_net` apps **and** the Mac mini stack (`macocr`, `omniscan`).|
|**pgAdmin 4**|`pgadmin`|`dpage/pgadmin4:latest`|**Portless** (Only within `proxy_net`)|`pgadmin.dungxbuif.com`|Graphic management console to administer postgres schemas and databases.|
|**n8n Automation**|`n8n`|`docker.n8n.io/n8nio/n8n:latest`|**Portless** (Only within `proxy_net`)|`n8n.dungxbuif.com`|Task scheduler and automation workflow engine connected to centralized PostgreSQL DB.|
|**CouchDB Obsidian Sync**|`couchdb`|`couchdb:3.3.3`|**Portless** (Only within `proxy_net`)|`couchdb.dungxbuif.com`  <br>`sync-db.dungxbuif.com`|CouchDB backend for Obsidian vault sync. Uses a dedicated `obsidian_vault` database and a non-admin sync user.|
|**My CV Web**|`my-cv`|Custom Dockerfile build|**Portless** (Only within `proxy_net`)|_(retired 2026-08)_|Static CV app. **Public `dungxbuif.com` now served by the Mac mini homepage** (`10.10.0.10:18081`); see [MAC.md](./MAC.md).|
|**GitLab Server**|`gitlab`|`gitlab/gitlab-ce:latest`|Host: `2222:22` (SSH)|`gitlab.dungxbuif.com`<br>`git.dungxbuif.com`|Centralized Git source code repository server (ARM64). Storage on `/ssd-data/infra/gitlab`. LAN-only. **⚠️ Stopped 2026-08 (operator decision).**|

---

## 🔑 Docker Registry Credentials & Shared CI/CD Spec

- **Domain Endpoint**: `https://registry.dungxbuif.com`
- **Authentication Engine**: HTTP Basic Authentication via Htpasswd (`/ssd-data/infra/registry/auth/htpasswd`)
- **Active Service User**: **`dungxbuif`**
- **Password Encryption**: Apache Bcrypt (`$2y$`)
- **Local Secret Reference**: `local_vars.json` $\rightarrow$ `LEGACY_SYSTEM_SECRETS.REGISTRY_USER` / `REGISTRY_PASSWORD`
- **Shared CI/CD Integration**:
  - GitLab CI variable `REGISTRY_USER`: `dungxbuif`
  - GitLab CI variable `REGISTRY_PASSWORD`: `<HIGH_ENTROPY_PASSWORD>`
  - Used by Kubernetes Runners for `docker login registry.dungxbuif.com -u "$REGISTRY_USER" --password-stdin` during CI/CD build stages.

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
        - Caddy: `./Caddyfile:/etc/caddy/Caddyfile` and `./caddy/data:/data`
        - RustFS: `./rustfs:/data` (S3 object storage files live cleanly inside `./rustfs`)
        - n8n Workflow Stack: `./n8n/n8n_storage:/home/node/.n8n`
        - PostgreSQL Central: `./postgres/data:/var/lib/postgresql/data`

### Rule 3: Smart Centralized Backup
The system implements an automated backup strategy to Google Drive to guarantee data safety:
*   **Tools:** `rclone` (Google Drive Integration) + `zip` + `pg_dump`.
*   **Strategy:**
    *   **PostgreSQL:** Automated daily `.sql` dumps prior to compression to ensure complete database transactional integrity.
    *   **Ingress & Application Data:** Backs up all critical configuration and persistent asset folders inside `/ssd-data/infra` (excluding temporary caches, runtime log files, and netdata profiles).
    *   **Frequency:** Every day at 01:00 AM local time.
    *   **Retention Policy:** Retains backups locally for 7 days (stored under `/tmp/backups`) and remotely on Google Drive for 30 days (stored under `server-backups` directory).

---

## 🪵 Key Troubleshooting Registry & Decisions

1. **AdGuard Home DNS Port 53 Conflict (2026-06-23)**: Disabled the `DNSStubListener` of `systemd-resolved` on Pi 5 OS to free port 53 (UDP/TCP) for the AdGuard Home container. This enables AdGuard to run stably and handle internal DNS queries (Split-horizon) for `*.dungxbuif.com` domains, preventing fallback to public Cloudflare (`1.1.1.1`).

---

## 🗄️ Database Management
All system databases are centrally hosted within the `postgres` container (fronted by PgBouncer on `:5432`) on the Raspberry Pi 5, and shared by both Pi5 `proxy_net` apps and the Mac mini production stack.
👉 Legacy inventory (K8s-era, but the DB list is still accurate): **[archived/k8s-v2/k8s/DB_INVENTORY.md](./archived/k8s-v2/k8s/DB_INVENTORY.md)**

---

## ⚡ Redis-Prod (v3 NEW)

A **standalone** Redis instance was added on the Pi5 to back the Mac mini stack
(macocr-proxy queue + omniscan-bot dedup/L2). It is intentionally **not** part of
the centralized `docker-compose.yml` because it binds a host port for LAN
access from the Mac:

| | |
---|---|
Compose | `/ssd-data/infra/redis-prod/docker-compose.yml` |
Image | `redis:7.2-alpine` (pinned, arm64) |
Bind | `0.0.0.0:16379` (uncommon port — avoids dev `6379` clashes) |
Auth | password (`requirepass`) — see `local_vars.json` |
Persistence | AOF (`appendonly yes`) |
Memory | `maxmemory 256mb`, `allkeys-lru` |

> [!NOTE]
> This is a **deliberate exception** to the portless principle: the Mac mini
> containers reach Redis over LAN at `10.10.0.5:16379`. It is the only Pi5 datastore
> with a host-port bind besides the sanctioned `caddy`/`adguardhome`/`rathole`.


1. **NEVER expose new host ports** in the `docker-compose.yml` unless explicitly requested. All new services must remain isolated inside the virtual virtual network `proxy_net`.
2. **NEVER use the generic `latest` tag** for system images in compose files. Pin down exact tags (e.g., `rustfs/rustfs:1.0.0-beta.3`, `postgres:16`) to guarantee runtime consistency and predictability.
3. **DO NOT run invasive host-level commands** with `sudo` if they prompt for password inputs. Leverage helper container volume mounts to modify files with root/non-root UID restrictions.
4. **ALWAYS keep verification scripts updated** inside `/ssd-data/scratch/` whenever security rules or credentials change to ensure CI/CD workflows and automatic verification procedures continue to pass cleanly.
5. **MANDATE ARM64 Compatibility:** Because this home lab runs on a single-board **Raspberry Pi 5 (ARM64 architecture)**, any new docker image or backend library added to compose must explicitly support the `linux/arm64` platform target. All compiled binaries inside `rathole-build` must target ARM instruction sets.
