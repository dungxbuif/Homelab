---
type: Reference
title: "Mac Mini Production Stack Specification"
description: "Specification of the Mac mini (10.10.0.10) Docker stack that runs user-facing workloads migrated off the K8s cluster"
timestamp: 2026-08-17T00:00:00Z
---

# 🍎 Mac Mini Production Stack Specification

> **Host:** Mac mini (Apple Silicon, arm64) — 12 cores / 48 GB RAM — LAN IP `10.10.0.10`.
> **Role:** Runs the **user-facing production workloads** that were migrated off the 3-node Proxmox K8s cluster.
> **Stack root:** `~/production/` (`/Users/dungxbuif/production/`).
> **Companion on Pi5:** Redis (`10.10.0.5:16379`) and PostgreSQL (`10.10.0.5:5432`).

This document is the canonical architecture spec for the Mac mini production stack.
The operator runbook lives alongside the stack at [`~/production/README.md`](../../../production/README.md).

---

## 🗺️ Topology & Routing

```
Internet --*.dungxbuif.com--> Cloud VPS (103.82.21.202)
   |  Rathole TCP :7000
   v
Pi5 (10.10.0.5) Caddy wildcard TLS (Cloudflare DNS-01)
   |  reverse_proxy over LAN
   +--> 10.10.0.10:18081  (homepage, dungxbuif.com)
   +--> 10.10.0.10:18080  (macocr-proxy, ocr.dungxbuif.com)
   +--> 10.10.0.10:1234   (LM Studio native, llm.dungxbuif.com)
   (omniscan-bot has NO public port — outbound Mezon bot only)

Mac mini 10.10.0.10  (Docker bridge network "homelab")
   ├── homelab-homepage      :18081->80   (registry image, amd64 via Rosetta)
   ├── homelab-macocr-proxy  :18080->8080 (built locally, calls native OCR)
   └── homelab-omniscan-bot   (no host port; Mezon bot + SSE client)

Native macOS services on the Mac host (NOT in Docker):
   ├── mac-ocr-native  *:8787  (Swift Vision OCR engine)
   └── LM Studio       *:1234  (local LLM endpoint; omniscan agent is DISABLED)
```

Containers reach the macOS-host native services via `host.docker.internal`
(because `network_mode: host` is a no-op on Docker Desktop for macOS — the
container network lives in a Linux VM and cannot see the macOS host namespace).

---

## 📦 Services

| Container | Service | Image | Host port | Public domain | Status |
|---|---|---|---|---|---|
| `homelab-homepage` | homepage | `registry.dungxbuif.com/homepage:prod-2026.08.06.2` | `18081`→80 | `dungxbuif.com` | amd64 image, runs via Rosetta on arm64 |
| `homelab-macocr-proxy` | macocr-proxy | `homelab/macocr-proxy:local` (built) | `18080`→8080 | `ocr.dungxbuif.com` | bridge→native OCR `:8787` |
| `homelab-omniscan-bot` | omniscan-bot | `homelab/omniscan-bot:local` (built) | — | — (Mezon bot) | **AI agent disabled** in build |

Redis (shared by macocr-proxy + omniscan-bot) runs on the Pi5, not the Mac:
`/ssd-data/infra/redis-prod/` → `10.10.0.5:16379` (auth, AOF). See [PI.md](./PI.md).

---

## 🧱 Stack Layout

```
~/production/
├── docker-compose.yml      # 3 services on bridge network "homelab"
├── .env                    # secrets (mode 600) — from homelab/local_vars.json
├── build/
│   ├── Dockerfile.macocr-proxy   # multi-stage: admin-ui (Vite) + docs (Docusaurus) + Go -> alpine
│   └── Dockerfile.omniscan-bot   # Go build + awk patch disabling the AI agent
├── caddy/
│   ├── Caddyfile.pi5.cutover     # applied on Pi5 at /ssd-data/infra/Caddyfile
│   └── README.md                 # cutover/rollback steps
└── README.md                     # operator runbook (status/logs/rebuild/cutover)
```

The mac-ocr source repo lives at `~/workspace/mac-ocr/` and is referenced as the
Docker build context. **The source repo is never modified** — all behaviour
changes (agent disable) are applied at build time via `awk` patches in the
Dockerfiles, keeping the repo pristine.

---

## 🔑 Key Design Decisions (verified)

1. **Bridge network, not `network_mode: host`.** On Docker Desktop for macOS,
   `--network host` lives in the Linux VM and CANNOT reach macOS-host services
   (native OCR `:8787`, LM Studio `:1234` → connection refused). Verified by test.
   Bridge network + `host.docker.internal` (resolves to the Mac host gateway) works.
2. **Uncommon host ports** (`18081`, `18080`) avoid clashing with developer
   containers already on this Mac (`postgres:5432`, `redis:6379`, `mongo:27017`).
   These ports are LAN-only and never exposed to the internet directly — Pi5 Caddy
   is the sole TLS edge.
3. **DB password URL-encoded** (`/`→`%2F`) in `DATABASE_URL`. The current Go
   `net/url` parser (in freshly built images) is stricter than the parser in the
   legacy K8s image `v1.0.2`, so a raw `/` in the password breaks URI parsing.
4. **AI agent disabled** in omniscan-bot via a build-time `awk` patch that stubs
   `handleThreadQuestion()` to reply with a "disabled on this host" message and
   return; `*scan` is additionally comment-gated in source. Only raw `*ocr`
   functions. The disabled message is baked into the binary (verified with
   `strings`).
5. **No Caddy on the Mac.** Pi5 Caddy is the only TLS edge (wildcard
   `*.dungxbuif.com` via Cloudflare DNS-01). Mac containers serve plain HTTP on
   LAN; Pi5 Caddy reverse-proxies to `10.10.0.10:<port>`. This is the literal
   "point Caddy at this machine" model — simplest possible cutover.

---

## 🔗 External Dependencies

- **PostgreSQL** — Pi5 `10.10.0.5:5432` (via PgBouncer), databases `macocr` &
  `omniscan`, user `admin`. See [PI.md](./PI.md).
- **Redis** — Pi5 `10.10.0.5:16379` (auth, AOF). See [PI.md](./PI.md).
- **S3 (macocr-proxy object storage)** — `https://storage.dungxbuif.com`
  (Pi5 RustFS), bucket `mac-ocr`.
- **Native OCR** — macOS app `mac-ocr-native` listening on `:8787` (Mac host).
- **LLM** — LM Studio on Mac `:1234` (referenced by the bot config, but the
  agent path is disabled).
- **Public DNS/TLS** — Cloudflare → VPS (`103.82.21.202`) Rathole → Pi5 Caddy →
  Mac/Pi5. See [MAIN.md](./MAIN.md).

---

## 🧰 Operations (quick reference)

Full runbook: [`~/production/README.md`](../../../production/README.md).

```bash
cd ~/production

# status / logs
docker compose ps
docker compose logs -f macocr-proxy     # or omniscan-bot / homepage

# restart after .env change
docker compose up -d --force-recreate

# rebuild after source change (build context = ~/workspace/mac-ocr)
docker build -f build/Dockerfile.macocr-proxy -t homelab/macocr-proxy:local ~/workspace/mac-ocr
docker build -f build/Dockerfile.omniscan-bot -t homelab/omniscan-bot:local ~/workspace/mac-ocr
docker compose up -d --force-recreate macocr-proxy omniscan-bot

# smoke tests
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:18080/healthz           # 200
docker exec homelab-macocr-proxy wget -qO- http://host.docker.internal:8787/capacity  # "ready"
curl -s -o /dev/null -w "%{http_code}\n" https://ocr.dungxbuif.com/healthz       # 200 (public)
curl -s -o /dev/null -w "%{http_code}\n" https://dungxbuif.com/                  # 200 (public)
```
