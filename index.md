---
type: Reference
title: "Homelab Infrastructure & Agent Gateway"
description: "Unified system overview, network topology, operational constraints, and documentation directory for the Homelab (v3 — Mac-centric production)"
timestamp: 2026-08-17T00:00:00Z
---

# 🏡 Homelab Infrastructure & Agent Gateway

🌐 **GitHub Repository:** [dungxbuif/Homelab](https://github.com/dungxbuif/Homelab)

Unified entry point and gateway for both human operators and AI agents. Covers
the hybrid cloud-edge topology, security principles, agent instructions,
operational constraints, and the documentation directory.

> **Architecture version: v3.1 (2026-08).** User-facing production workloads run
> on the **Mac mini** (`10.10.0.10`). The **Orange Pi Zero 3** (`10.10.0.2`) is the
> TLS edge (Caddy+Rathole+AdGuard via Docker Swarm). The **Pi5** (`10.10.0.5`) is
> the datastore and object storage backend (Swarm manager). The **Cloud VPS** (`103.82.21.202`) is the public
> boundary. The **Proxmox** host (`10.10.0.20`) was repurposed as a self-hosted
> AWS practice lab — the 3-node K8s cluster was retired (history archived in
> [`docs/archived/k8s-v2/`](./docs/archived/k8s-v2/)).

---

## 🗺️ Network Topology

```text
       +-------------------------------------------------------+
       |                  Cloud VPS (Edge Gateway)              |
       |  Public IP: 103.82.21.202  /  Tailnet: 100.64.0.2     |
       |  - Nginx SNI/HTTP Whitelist -> Rathole Tunnel Server  |
       |  - Direct SSL: transfer., headscale.dungxbuif.com     |
       |  - Headscale + UI, PairDrop, Coturn, bds-app,         |
       |    bds-prod-db (Postgres), RustDesk hbbs/hbbr, wg0    |
       +---------------------------+---------------------------+
                                   |
                TCP Rathole (:7000)|  Headscale Tailnet (100.64.0.0/10)
                                   v
       +-------------------------------------------------------+
       |           Orange Pi Zero 3 (TLS Edge Gateway)         |
       |  LAN: 10.10.0.2  /  Docker Swarm worker               |
       |  Caddy wildcard TLS (Cloudflare DNS-01), AdGuard DNS  |
       |  Rathole client → VPS                                 |
       |  homelab-net overlay → Pi5 datastores                 |
       +---------------------------+---------------------------+
                                   |
                Docker Swarm overlay (homelab-net, 172.30.0.0/16)
                                   |
       +-------------------------------------------------------+
       |              Raspberry Pi 5 (Datastore & Storage)     |
       |  LAN: 10.10.0.5  /  Swarm Manager (Leader)            |
       |  Tailnet: 100.64.0.1  /  Subnet Router 10.10.0.0/24   |
       |  proxy_net: n8n, RustFS(S3), Registry, LibreSpeed,     |
       |    Postgres+PgBouncer, pgAdmin, CouchDB, GitLab,       |
       |    GoClaw, monitoring (8 containers on overlay)       |
       |  Redis-prod: 10.10.0.5:16379 (auth, AOF)              |
       +--------+-----------------------+----------------------+
                |                       |  reverse_proxy over LAN
                v                       v
       +-------------------+   +--------------------------------+
       | MikroTik hEX S    |   | Mac mini 10.10.0.10            |
       | 10.10.0.1         |   | PRODUCTION (v3):               |
       | PPPoE/VLAN35,DHCP |   |  homelab-homepage   :18081     |
       | NAT, FastTrack    |   |  homelab-macocr-proxy :18080   |
       +---+----------+----+   |  homelab-omniscan-bot (no port)|
           |          |        | Native: mac-ocr-native :8787   |
           v          v        |         LM Studio     :1234   |
       +------+   +----------+ +--------------------------------+
       |MeshAP |   | Proxmox VE 10.10.0.20 (Tailnet 100.64.0.3) |
       |bridge |   | AWS LAB (repurposed): LocalStack, eksctl,  |
       +------+   | k3s practice VMs (ephemeral). K8s retired.  |
                  +--------------------------------------------+
```

---

## 🛡️ Security & Design Principles

### 1. Portless Security Invariant (with one deliberate exception)
No home-router ports are opened/forwarded to the internet.
- Inbound `*.dungxbuif.com` traffic lands on the **Cloud VPS**.
- The **Orange Pi Zero 3** opens outbound Rathole tunnels back to the VPS;
  **Caddy** on the orange-pi terminates TLS (Cloudflare DNS-01 wildcard) and
  routes to portless `proxy_net` containers on the Pi5 via a Docker Swarm
  overlay (`homelab-net`).
- **Deliberate exception — the Mac mini.** Because there is no Caddy on the Mac
  and orange-pi Caddy must reach the stack over LAN, the Mac containers expose
  **uncommon** LAN-only host ports (`18081`, `18080`, …), chosen to avoid dev
  ports (`5432`, `6379`, `27017`) and existing Mac containers. These ports are
  never directly internet-reachable — only orange-pi Caddy proxies to them.

### 2. Infrastructure as Code (IaC)
- **Terraform (OpenTofu)** provisions VMs on the Proxmox API.
- **Ansible** configures VM OSes and installs runtimes.
- Current scope: **AWS lab VMs** (LocalStack / eksctl / k3s). The K8s cluster
  IaC state is preserved under `iac/terraform/` until teardown is confirmed.

### 3. Local Variables Isolation
All sensitive values (public VPS IP, SSH passwords, DB credentials, API keys,
client secrets, private keys) live in gitignored [`local_vars.json`](./local_vars.json)
and the gitignored `credentials/` folder. Public files use placeholders.

---

## 🤖 AI Agent Gateway & Operational Constraints

> [!IMPORTANT]
> **MANDATORY INVARIANT:** every AI agent starting a new session must read this
> `index.md` first to orient itself, before opening sub-documents.

### 📌 Operational Constraints (Strict Invariants)

1. **Gateway entry point** — read this file first; open sub-documents only as needed.
2. **Context synchronization** — every design decision / architectural change /
   human-AI agreement is recorded in [`docs/LOG.md`](./docs/LOG.md). Summarize old
   items; fully document new/in-progress ones.
3. **Portless constraint** — never expose host `ports:` for new Pi5 `proxy_net`
   services. The Mac mini stack (`~/production/`) is the sanctioned exception,
   using uncommon LAN-only ports as above.
4. **Architecture compatibility** — Pi5 images must support `linux/arm64`; Mac
   images may be `arm64` (native) or `amd64` (Rosetta), preferring arm64-native.
5. **Sensitive variables** — load secrets from `local_vars.json` / `credentials/`,
   never hard-code them.
6. **No direct engine/DB mutation** — do not alter credentials or fix issues via
   raw engine runners (e.g. `gitlab-rails runner`) or raw SQL without explicit
   human approval; use app UIs, official APIs, or IaC/GitOps manifests.
7. **mac-ocr source is read-only** — never edit `~/workspace/mac-ocr/` to change
   behaviour; apply changes at build time via patches in `~/production/build/`.
8. **Proxmox lab is ephemeral** — lab VMs are disposable; back up state before
   any `terraform destroy`.

### 🗺️ Homelab System Snapshot

* **Public edge ingress:** Cloud VPS (`103.82.21.202`) → Rathole (`:7000`) →
  Orange Pi Caddy. The VPS enforces a strict **domain whitelist** at the Nginx layer;
  new public domains must be added on the VPS — see the
  [Service Export Playbook](docs/MAIN.md#-service-export-playbook-end-to-end-v3).
* **TLS edge:** Orange Pi Zero 3 (`10.10.0.2`) — Caddy, Rathole client, AdGuard
  Home DNS, Docker Swarm worker.
* **Datastore & persistent services:** Pi5 (`10.10.0.5`) — Postgres +
  PgBouncer (`:5432`), Redis-prod (`:16379`), RustFS (S3), Registry, n8n,
  LibreSpeed, pgAdmin, CouchDB, GitLab, GoClaw, monitoring stack. Docker
  Swarm manager.
* **Production compute:** Mac mini (`10.10.0.10`) — homepage, macocr-proxy,
  omniscan-bot. See [docs/MAC.md](./docs/MAC.md).
* **Core router:** MikroTik hEX S (`10.10.0.1`) — PPPoE/VLAN35, DHCP, NAT, FastTrack.
* **Lab hypervisor:** Proxmox VE (`10.10.0.20`) — AWS practice lab. See
  [docs/PROXMOX.md](./docs/PROXMOX.md).

### 📝 Decisions & Context Synchronization
📜 **[docs/LOG.md](./docs/LOG.md) — Directory Update Log**

---

## 📂 Documentation Directory

Deep-dive docs live in `docs/`:

* 📖 **[docs/MAIN.md](./docs/MAIN.md) — System Context & Playbook** — full v3 topology, Caddy/Rathole, the service-export playbook, and the bug/optimization registry.
* 🍓 **[docs/PI.md](./docs/PI.md) — Pi5 Datastore Specification** — Pi5 datastore & persistent services: Postgres+PgBouncer, Redis-prod, RustFS, Registry, n8n, monitoring, Docker Swarm manager.
* 🍎 **[docs/MAC.md](./docs/MAC.md) — Mac Mini Production Stack** — homepage / macocr-proxy / omniscan-bot; native OCR bridge; build-time agent-disable; operations runbook pointer.
* 🛜 **[docs/MIKROTIK.md](./docs/MIKROTIK.md) — MikroTik Router Configuration** — PPPoE, DHCP, return-path routing for VPN clients, security hardening.
* 🖥️ **[docs/PROXMOX.md](./docs/PROXMOX.md) — Proxmox Guide (AWS Lab Repurpose)** — Proxmox repurposed as a self-hosted AWS practice lab; K8s history archived.
* 📜 **[docs/PRE_REQUIRE.md](./docs/PRE_REQUIRE.md) — Proxmox IaC Prerequisites** — API tokens & SSH keys for Terraform/Ansible.
* 🔬 **[docs/CONTEXT.md](./docs/CONTEXT.md) — Network Diagnostic Trace** — benchmarks, latency, and DNS troubleshooting history.
* 🔁 **[docs/COUCHDB_OBSIDIAN_SYNC.md](./docs/COUCHDB_OBSIDIAN_SYNC.md) — CouchDB Obsidian Sync** — deployment, client settings, recovery notes.
* 📐 **[docs/OKF_SPEC.md](./docs/OKF_SPEC.md) — Open Knowledge Format (OKF)** — the OKF v0.1 standard used across this bundle.
* 🗄️ **[docs/archived/INDEX.md](./docs/archived/INDEX.md) — Archived Legacy Docs** — retired K8s-era documentation (cluster bootstrap, Longhorn, recovery, CICD, monitoring, benchmarks).
