# Historical snapshot - not a current runbook

Preserved before the 2026-09-16 documentation audit. Original location: `index.md`.
Relative links in the snapshot retain their original context.

---
type: Reference
title: "Homelab Infrastructure & Agent Gateway"
description: "Unified system overview, network topology, operational constraints, and documentation directory for the Homelab (v3.2 — VM100 production)"
timestamp: 2026-09-11T00:00:00+07:00
---

# 🏡 Homelab Infrastructure & Agent Gateway

🌐 **GitHub Repository:** [dungxbuif/Homelab](https://github.com/dungxbuif/Homelab)

Unified entry point and gateway for both human operators and AI agents. Covers
the hybrid cloud-edge topology, security principles, agent instructions,
operational constraints, and the documentation directory.

> **Architecture version: v3.2 (2026-09).** User-facing production workloads run
> on **VM100** (`10.10.0.31`). The **Orange Pi Zero 3** (`10.10.0.2`) is the
> home edge (Traefik+Rathole+AdGuard via Docker Swarm). The **Pi5** (`10.10.0.5`)
> is the datastore and object storage backend (Swarm manager). The **Mac mini**
> (`10.10.0.6`) provides native OCR and local development dependencies; MyPocket
> remains outside the VM100 migration while under development. The **Cloud VPS**
> (`103.82.21.202`) is the public boundary and now runs only
> `gateway-traefik`, `rathole-server`, and retained SQL snapshots. Headscale,
> NetBird, Coturn, RustDesk, node-exporter, and Tailscale were removed on
> 2026-09-13. The **Proxmox** host
> (`10.10.0.20`) was repurposed as a self-hosted AWS practice lab — the 3-node
> K8s cluster was retired (history archived in
> [`docs/archived/k8s-v2/`](./docs/archived/k8s-v2/)).

---

## 🗺️ Network Topology

```text
       +-------------------------------------------------------+
       |                  Cloud VPS (Edge Gateway)              |
       |  Public IP: 103.82.21.202                             |
       |  - gateway-traefik -> Rathole tunnel server           |
       |  - retained BDS SQL snapshots under /root/backup-bds  |
       +---------------------------+---------------------------+
                                   |
                TCP Rathole (:7000)|
                                   v
       +-------------------------------------------------------+
       |           Orange Pi Zero 3 (TLS Edge Gateway)         |
       |  LAN: 10.10.0.2  /  Docker Swarm worker               |
       |  edge_traefik wildcard TLS, edge_adguardhome DNS      |
       |  edge_rathole client -> VPS                           |
       |  homelab-net overlay → Pi5 datastores                 |
       +---------------------------+---------------------------+
                                   |
                Docker Swarm overlay (homelab-net, 172.30.0.0/16)
                                   |
       +-------------------------------------------------------+
       |              Raspberry Pi 5 (Datastore & Storage)     |
       |  LAN: 10.10.0.5  /  Swarm Manager (Leader)            |
       |  Datastores/services: RustFS, Registry, LibreSpeed,    |
       |    Postgres+PgBouncer, pgAdmin, CouchDB                |
       |  Redis-prod: 10.10.0.5:16379 (auth, AOF)              |
       +--------+-----------------------+----------------------+
                |                       |  reverse_proxy over LAN
                v                       v
       +-------------------+   +--------------------------------+
       | MikroTik hEX S    |   | VM100 10.10.0.31               |
       | 10.10.0.1         |   | PRODUCTION COMPUTE:            |
       | PPPoE/VLAN35,DHCP |   |  homepage          :18081      |
       | NAT, FastTrack    |   |  macocr-proxy      :18080      |
       +---+----------+----+   |  mezonhook         :18084      |
           |          |        |  family-tree       :18085      |
           |          |        +--------------------------------+
           v          v        | Mac mini 10.10.0.6             |
       +------+   +----------+ | Native OCR :8787, LM Studio    |
       |MeshAP |   | Proxmox VE 10.10.0.20                    |
       |bridge |   | AWS LAB (repurposed): LocalStack, eksctl,  |
       +------+   | k3s practice VMs (ephemeral). K8s retired.  |
                  +--------------------------------------------+
```

---

## 🛡️ Security & Design Principles

### 1. Portless Security Invariant (with explicit LAN-only exceptions)
No home-router ports are opened/forwarded to the internet.
- Inbound `*.dungxbuif.com` traffic lands on the **Cloud VPS**.
- The **Orange Pi Zero 3** opens outbound Rathole tunnels back to the VPS;
  **Traefik** on the Orange Pi terminates TLS (Cloudflare DNS-01 wildcard) and
  routes to portless `proxy_net` containers on the Pi5 via a Docker Swarm
  overlay (`homelab-net`).
- **LAN-only service exceptions — VM100 and Mac dependencies.** VM100 exposes
  uncommon LAN-only app ports (`18081`, `18080`, `18084`, `18085`) for Orange Pi
  Traefik upstreams. The Mac exposes native dependency ports such as OCR
  `:8787` and LM Studio `:1234`. These ports are never directly
  internet-reachable.

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
7. **mac-ocr source is read-only** — never edit
   `~/workspace/homelab/projects/mac-ocr/` to change behaviour; apply changes at
   build/deployment time instead.
8. **Proxmox lab is ephemeral** — lab VMs are disposable; back up state before
   any `terraform destroy`.
9. **Local project aggregation** — active project source checkouts are under
   `~/workspace/homelab/projects/` and are gitignored from the Homelab infra
   repo. `MyPocket` is the explicit exception and remains at
   `~/workspace/MyPocket/`; see [docs/PROJECTS.md](./docs/PROJECTS.md).

### 🗺️ Homelab System Snapshot

* **Public edge ingress:** Cloud VPS `gateway-traefik` (`103.82.21.202`) ->
  Rathole (`:7000`) -> Orange Pi `edge_traefik`. Public hostnames must be added
  to the VPS Traefik HostSNI allow-list and the Orange Pi dynamic config; see the
  [Service Export Playbook](docs/MAIN.md#-service-export-playbook-end-to-end-v3).
* **TLS edge:** Orange Pi Zero 3 (`10.10.0.2`) — Traefik, Rathole client, AdGuard
  Home DNS, Docker Swarm worker.
* **Datastore & persistent services:** Pi5 (`10.10.0.5`) — Postgres +
  PgBouncer (`:5432`), Redis-prod (`:16379`), RustFS (S3), Registry,
  LibreSpeed, pgAdmin, and CouchDB. Docker
  Swarm manager.
* **Production compute:** VM100 (`10.10.0.31`) — homepage, macocr-proxy,
  Family Tree, and MezonHook. See [docs/VM100.md](./docs/VM100.md).
* **Mac runtime dependencies:** Mac mini (`10.10.0.6`) — native OCR and
  LM Studio; MyPocket remains local/dev and is intentionally not migrated. See
  [docs/MAC.md](./docs/MAC.md).
* **Core router:** MikroTik hEX S (`10.10.0.1`) — PPPoE/VLAN35, DHCP, NAT, FastTrack.
* **Lab hypervisor:** Proxmox VE (`10.10.0.20`) — AWS practice lab. See
  [docs/PROXMOX.md](./docs/PROXMOX.md).

### 📝 Decisions & Context Synchronization
📜 **[docs/LOG.md](./docs/LOG.md) — Directory Update Log**

---

## 📂 Documentation Directory

Deep-dive docs live in `docs/`:

* 📖 **[docs/MAIN.md](./docs/MAIN.md) — System Context & Playbook** — current VPS Traefik -> Rathole -> Orange Pi Traefik topology, service-export playbook, and bug/optimization registry.
* 🍓 **[docs/PI.md](./docs/PI.md) — Pi5 Datastore Specification** — Pi5 datastore & persistent services: Postgres+PgBouncer, Redis-prod, RustFS, Registry, and Docker Swarm manager.
* 🖥️ **[docs/VM100.md](./docs/VM100.md) — VM100 Production Compute** — homepage / macocr-proxy / Family Tree / MezonHook and Orange Pi Traefik upstreams.
* 🍎 **[docs/MAC.md](./docs/MAC.md) — Mac Mini Runtime Dependencies** — native OCR and LM Studio dependencies; MyPocket stays local/dev.
* 🛜 **[docs/MIKROTIK.md](./docs/MIKROTIK.md) — MikroTik Router Configuration** — PPPoE, DHCP, return-path routing for VPN clients, security hardening.
* 🖥️ **[docs/PROXMOX.md](./docs/PROXMOX.md) — Proxmox Guide (AWS Lab Repurpose)** — Proxmox repurposed as a self-hosted AWS practice lab; K8s history archived.
* 📜 **[docs/PRE_REQUIRE.md](./docs/PRE_REQUIRE.md) — Proxmox IaC Prerequisites** — API tokens & SSH keys for Terraform/Ansible.
* 🔬 **[docs/CONTEXT.md](./docs/CONTEXT.md) — Network Diagnostic Trace** — benchmarks, latency, and DNS troubleshooting history.
* 🔁 **[docs/COUCHDB_OBSIDIAN_SYNC.md](./docs/COUCHDB_OBSIDIAN_SYNC.md) — CouchDB Obsidian Sync** — deployment, client settings, recovery notes.
* 📐 **[docs/OKF_SPEC.md](./docs/OKF_SPEC.md) — Open Knowledge Format (OKF)** — the OKF v0.1 standard used across this bundle.
* 📂 **[docs/PROJECTS.md](./docs/PROJECTS.md) — Local Project Workspace Layout** — project source aggregation under `~/workspace/homelab/projects/`, with MyPocket kept outside.
* 🗄️ **[docs/archived/INDEX.md](./docs/archived/INDEX.md) — Archived Legacy Docs** — retired K8s-era documentation (cluster bootstrap, Longhorn, recovery, CICD, monitoring, benchmarks).
