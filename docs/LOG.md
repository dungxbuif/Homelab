---
type: Reference
title: 'Directory Update Log'
description: 'Changelog and historical context updates for the Homelab documentation files'
timestamp: 2026-07-03T15:14:00Z
---

# Directory Update Log

## 2026-08-17 — v3: Mac mini consolidation + Proxmox AWS lab repurpose

- **Architecture version bump to v3.** Migrated all user-facing production workloads off the 3-node Proxmox K8s cluster (`k8s-cp-1/2/3`, VIP `10.10.0.30`) onto the **Mac mini** (`10.10.0.10`, Apple Silicon, Docker Compose). The Pi5 (`10.10.0.5`) remains the sole TLS edge (Caddy, Cloudflare DNS-01 wildcard) and now also hosts **Redis-prod** for the Mac stack. The K8s cluster is retired; Proxmox (`10.10.0.20`) is repurposed as a self-hosted **AWS practice lab** (LocalStack / eksctl / k3s).
- **Mac mini production stack** (`~/production/`): three containers on a bridge network `homelab` — `homelab-homepage` (`:18081`, registry image, amd64 via Rosetta), `homelab-macocr-proxy` (`:18080`, built locally), `homelab-omniscan-bot` (no host port, Mezon bot). Spec: [MAC.md](./MAC.md). Runbook: `~/production/README.md`.
- **Native OCR bridge:** the proxy reaches the macOS-host Swift OCR engine (`mac-ocr-native :8787`) via `host.docker.internal`. Verified that `network_mode: host` is a no-op on Docker Desktop for macOS (Linux VM cannot see the macOS host) — must use bridge + `host.docker.internal`. Documented in [MAIN.md](./MAIN.md) bug registry #7.
- **AI agent disabled** on omniscan-bot via a build-time `awk` patch stubbing `handleThreadQuestion()` (source repo `~/workspace/mac-ocr/` left untouched). Only `*ocr` works. Disabled message baked into the binary.
- **Redis-prod on Pi5** (`/ssd-data/infra/redis-prod/`, `redis:7.2-alpine`, bind `0.0.0.0:16379`, auth, AOF, 256mb LRU) — deliberate portless-principle exception so Mac containers can reach it over LAN. Documented in [PI.md](./PI.md).
- **DB password URL-encoding:** the `/` in the Postgres password broke the stricter `net/url` parser in freshly built images (legacy K8s `v1.0.2` tolerated it). URL-encoded as `%2F` in `DATABASE_URL`. Documented in [MAIN.md](./MAIN.md) bug registry #8.
- **Caddy cutover (Pi5):** live `/ssd-data/infra/Caddyfile` updated to route `dungxbuif.com`→`10.10.0.10:18081` and `ocr.dungxbuif.com`→`10.10.0.10:18080`; `grafana.dungxbuif.com` and the K8s-only routes (`localstack/longhorn/argocd/traefik/portainer`) retired. Backup at `/ssd-data/infra/Caddyfile.bak-20260817190337`. Source: `~/production/caddy/Caddyfile.pi5.cutover`. Verified `dungxbuif.com`/`ocr.dungxbuif.com`→200, `grafana`→404.
- **K8s cleanup:** deleted ArgoCD `homepage-prod` Application (stop GitOps self-heal) and the app namespaces `homepage-prod`, `homepage-dev`, `macocr`, `omniscan`, `redis`, `localstack`, `monitoring`, `gitlab-runner`. Remaining on K8s: `argocd`, `traefik`, `longhorn-system`, `kube-system` (cluster infra — to be destroyed with the Proxmox VMs separately).
- **GitLab on Pi5** stopped temporarily (operator decision).
- **Docs restructure (this entry):** archived the K8s-era docs into [./archived/k8s-v2/](./archived/k8s-v2/) (`docs/k8s/`, `monitoring/`, `2026-05-29_k8s_proxmox_iac_design.md`, `PROXMOX.md`→`PROXMOX.k8s.md`, `goclaw_implementation_plan.md`, OCR benchmark reports). Rewrote the core docs to v3: [index.md](../index.md), [MAIN.md](./MAIN.md), [INDEX.md](./INDEX.md), [PROXMOX.md](./PROXMOX.md); added [MAC.md](./MAC.md) and [archived/INDEX.md](./archived/INDEX.md); updated [PI.md](./PI.md) (Redis-prod, Mac bridge, retired routes). Note: pre-2026-08-17 entries below contain links to the old `./k8s/...` and `./monitoring/...` paths — those files have moved to `./archived/k8s-v2/`. The old `./PROXMOX.md` (K8s cluster) is now `./archived/k8s-v2/PROXMOX.k8s.md`; `./PROXMOX.md` is the new AWS-lab version. See the archived index.

## 2026-08-04

- **Headscale & Tailnet Mesh Migration (WireGuard Decommissioned)**: Decommissioned and cleaned up the legacy `wg0` WireGuard interfaces across the Cloud VPS (`103.82.21.202`) and Raspberry Pi 5 (`10.10.0.5`). Deployed Headscale Control Server (`headscale/headscale:v0.25.0`) on the Cloud VPS (`103.82.21.202`) behind Nginx direct SSL termination (`https://headscale.dungxbuif.com`) with embedded DERP relay server on port `3478/udp` and MagicDNS domain `homelab.net`. Enrolled Raspberry Pi 5 (`100.64.0.1`, Subnet Router for `10.10.0.0/24`), Cloud VPS (`100.64.0.2`), and Proxmox VE Hypervisor (`100.64.0.3`) into the P2P Tailnet mesh. Verified sub-5ms P2P direct latency and full cross-node access over Tailnet.

## 2026-08-03

- **PairDrop & Coturn Direct VPS Deployment**: Deployed PairDrop (`lscr.io/linuxserver/pairdrop:latest`) and Coturn STUN/TURN Server (`coturn/coturn:4.6.2`) directly on the Cloud VPS (`103.82.21.202`). Copied wildcard TLS certs (`*.dungxbuif.com`) to `/root/gateway/certs/` on the VPS to enable **direct SSL termination on Nginx Gateway** (`127.0.0.1:8443`), eliminating any hairpin routing back to the Raspberry Pi 5 at home. PairDrop web ingress is served via `https://transfer.dungxbuif.com` with Coturn STUN/TURN on port `3478` (TCP/UDP).

## 2026-07-30

- **IT-Tools Deployment**: Deployed IT-Tools (`corentinth/it-tools:latest`) as a portless Docker container service on the Raspberry Pi 5 (`10.10.0.5`) running inside `proxy_net`. Added ingress routing block for `tools.dungxbuif.com` in Caddyfile (`reverse_proxy it-tools:80`), and added `tools.dungxbuif.com` to the Nginx SNI and HTTP host whitelists on the Cloud VPS gateway (`103.82.21.202`) for public internet accessibility.

## 2026-07-15

- **RustFS Storage**: Created a new S3-compatible bucket `whiteboard` on the RustFS object storage running on the Raspberry Pi 5. Configured a dedicated user/access key `whiteboard` with secret key `<WHITEBOARD_MINIO_SECRET_KEY>` and attached a custom read/write policy `whiteboard-policy` scoped strictly to the `whiteboard` bucket. Added `WHITEBOARD _MINIO_ACCESS_KEY` to `local_vars.json` as the local source of truth.

## 2026-07-09

- **Kubernetes/AWS Lab**: Added a LAN-only LocalStack deployment for AWS SAA practice under [iac/k8s/localstack/README.md](../iac/k8s/localstack/README.md). The deployment uses namespace `localstack`, ClusterIP service, Traefik Ingress host `localstack.dungxbuif.com`, Longhorn PVC persistence, and no NodePort/direct LoadBalancer. Lab endpoints are `https://localstack.dungxbuif.com` from LAN clients, `http://localstack.localstack.svc.cluster.local:4566` inside K8s, and `http://localhost:4566` through `kubectl port-forward` as fallback. Docker-in-Docker and privileged mode are disabled by default; Lambda/container-runtime behavior must be enabled only by a separate security decision. The image is pinned to `localstack/localstack:3.8.1` because current latest/stable images require `LOCALSTACK_AUTH_TOKEN`.

## 2026-07-08

- **CouchDB/Obsidian Sync**: Deployed CouchDB on the Raspberry Pi 5 Docker stack as a portless `proxy_net` service. Added Caddy routing for `couchdb.dungxbuif.com` and `sync-db.dungxbuif.com`, added the same host whitelist entries on the Cloud VPS Nginx gateway, and created a dedicated `obsidian_vault` database with a non-admin sync user for Obsidian vault replication. Runbook: [COUCHDB_OBSIDIAN_SYNC.md](./COUCHDB_OBSIDIAN_SYNC.md).
- **VPN/WireGuard**: Resolved the SSH inaccessibility issue on the Raspberry Pi when connected to the VPN from outside the LAN. Added `PersistentKeepalive = 25` to `/etc/wireguard/wg0.conf` on the Pi and restarted the `wg0` interface. This prevents the home router from closing the UDP NAT session mappings, ensuring the Pi remains reachable from all VPN peers.

## 2026-07-04

- **Consolidation**: Consolidated root files (`AGENT.md`, `README.md`, and `index.md`) into a single unified `index.md` serving as the gateway and infrastructure overview for the Homelab repository. Removed deprecated `AGENT.md` and `README.md` files and updated all relevant references across the workspace.

## 2026-06-25

- **Database/PgBouncer**: Configured a centralized connection pooler (**PgBouncer**) running in `transaction` pool mode, exposed on port `5432` on the Pi 5. Kept the raw `postgres` container hidden inside the Docker `proxy_net` network to enforce access isolation.

## 2026-06-24

- **DNS/AdGuard Home**: Added multiple resilient upstream resolvers (`https://dns.google/dns-query`, `https://cloudflare-dns.com/dns-query`, `1.1.1.1`, `8.8.8.8`) and bootstrap DNS servers to `AdGuardHome.yaml` on the Raspberry Pi 5. This resolved local network DNS resolution dropouts caused by timeouts and `unexpected EOF` connection failures when querying the single previous DoH upstream (`https://dns10.quad9.net/dns-query`).

## 2026-06-23

- **DNS**: Disabled `DNSStubListener` of `systemd-resolved` on Raspberry Pi 5 to free port 53 for AdGuard Home.
- **Restructure**: Restructured the documentation directory to follow the Open Knowledge Format (OKF) standard (v0.1) and translated all contents from Vietnamese to English. Created root and subdirectory indexes: [INDEX.md](./INDEX.md), [k8s/INDEX.md](./k8s/INDEX.md), [monitoring/INDEX.md](./monitoring/INDEX.md). Converted concepts: [2026-05-29_k8s_proxmox_iac_design.md](./2026-05-29_k8s_proxmox_iac_design.md), [CONTEXT.md](./CONTEXT.md), [MAIN.md](./MAIN.md), [MIKROTIK.md](./MIKROTIK.md), [PI.md](./PI.md), [PRE_REQUIRE.md](./PRE_REQUIRE.md), [PROXMOX.md](./PROXMOX.md), [k8s/CICD.md](./k8s/CICD.md), [k8s/DB.md](./k8s/DB.md), [k8s/DB_INVENTORY.md](./k8s/DB_INVENTORY.md), [k8s/LONGHORN_CONFIG_REVIEW.md](./k8s/LONGHORN_CONFIG_REVIEW.md), [k8s/RECOVERY_GUIDE.md](./k8s/RECOVERY_GUIDE.md), [monitoring/README.md](./monitoring/README.md). Added the official specification reference: [OKF_SPEC.md](./OKF_SPEC.md).

- **Fix**: Resolved the K8s DNS query loops for `kubernetes.nccsoft.office` by:
   - Replacing the `nccsoft.office` search domain with `lan` in Netplan configs on K8s nodes `k8s-cp-1`, `k8s-cp-2`, `k8s-cp-3` and running `netplan apply`.
   - Updating `iac/terraform/main.tf` to explicitly specify `searchdomain = "lan"` to prevent future regressions.
   - Modifying `/etc/resolv.conf`, `/etc/hosts`, and `/etc/postfix/main.cf` on the Proxmox host (`10.10.0.20`) to replace `nccsoft.office` with `lan`.

## 2026-06-06

- **Database**: Centrally hosted all PostgreSQL databases in the lab on Raspberry Pi 5 (`postgres.dungxbuif.com`).

## 2026-06-03

- **CI/CD**: Replaced self-hosted GitLab on Pi 5 with GitHub Actions (ARC) + ArgoCD to conserve RAM.
- **Restructure**: Moved sub-documentation files (`MAIN.md`, `PI.md`, `CONTEXT.md`) into `/docs/`.
- **Gateway**: Renamed root `README.md` to `AGENT.md` as the mandatory AI agent gateway.
- **Storage**: Selected Longhorn v1.7.x for manual installation (replica count 2).
- **Ingress**: Established Traefik Ingress on K8s VIP `10.10.0.30` with Caddy as the main entry proxy.
- **Topology**: Joined nodes `k8s-cp-2` and `k8s-cp-3` to cluster and installed Cilium CNI.
