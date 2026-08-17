---
type: Playbook
title: "GoClaw Service Setup on Kubernetes"
description: "Configuration deployment specifications for GoClaw web components, microservices, and network policies"
timestamp: 2026-07-03T15:14:00Z
---

# GoClaw Workload Operations & Local Docker Deployment Manual

This document details the purpose, setup instructions, network architecture, and troubleshooting history for the **GoClaw** application (`nextlevelbuilder/goclaw`) deployed directly on the Raspberry Pi 5.

---

## 🎯 Purpose & Description

**GoClaw** is a lightweight, high-performance gateway and execution manager designed for **Claude Code** and autonomous developer agentic workflows. 
*   **Centralized Context & Tool Registry**: It serves as a centralized hub that stores agent sessions, runs, and registers tools (MCP servers, custom terminal tools).
*   **Episodic Memory Backend**: It integrates with a vector database (via PostgreSQL `pgvector`) to provide agents with a semantic search backend for long-term memory, recall, and context layering.
*   **Execution Controller**: It acts as an execution approval gate, allowing humans in the loop to safely monitor and approve terminal operations proposed by background agents.

---

## 🏗️ Architecture & Topology (Local Docker Deployment)

GoClaw runs as a Docker container directly on the Raspberry Pi 5, isolated inside the virtual virtual network `proxy_net`. It is completely hidden from the host network and external clients, with traffic proxied exclusively through Caddy.

```text
                                       [ Local Network / VPN Client ]
                                                     │
                                                     ▼ (HTTPS)
                                        [ Raspberry Pi 5 Gateway ]
                                         (Caddy: 10.10.0.5:443)
                                                     │
                                                     ▼ (Internal Proxy)
                                              [ GoClaw Container ]
                                           (Docker Service: goclaw:18790)
                                                     │
                                                     ▼ (Direct Container Link)
                                         [ PostgreSQL Container ]
                                          (Docker Service: postgres:5432)
```

### 1. Resource Allocations & Isolation
GoClaw is built from source directly on the Pi 5 using a multi-stage Dockerfile:
*   **Build arguments**:
    *   `ENABLE_EMBEDUI=true` (packages and embeds the Web Console UI).
    *   `ENABLE_FULL_SKILLS=true` (pre-installs Python and Node runtimes for skill execution).
    *   `ENABLE_CLAUDE_CLI=true` (packages Claude Code inside the runtime).
*   **Network Isolation**: Exposes only port `18790` internally inside `proxy_net`. Zero host ports are mapped on the Pi 5.

### 2. Persistent Storage
Data is mapped directly to the Pi 5 NVMe SSD:
*   **Data directory**: `./goclaw/data` mounted to `/app/data` (stores configuration, database config, and dynamic tool states).
*   **Workspace directory**: `./goclaw/workspace` mounted to `/app/workspace` (working directory for running agent tasks).
*   *Note*: The directories on the host must be owned by UID `1000` (`dungxbuif`) to avoid write permission errors inside the container.

### 3. Database Connection
*   GoClaw connects directly to the `postgres` container on `postgres:5432` inside `proxy_net`, bypassing PgBouncer and avoiding pooler connection limits:
    `GOCLAW_POSTGRES_DSN=postgres://goclaw_user:<password>@postgres:5432/goclaw?sslmode=disable`

---

## 🛠️ Docker Compose Configuration

The GoClaw service is configured inside `/ssd-data/infra/docker-compose.yml` on the Pi 5:

```yaml
  goclaw:
    build:
      context: /ssd-data/goclaw
      args:
        - ENABLE_EMBEDUI=true
        - ENABLE_FULL_SKILLS=true
        - ENABLE_CLAUDE_CLI=true
    container_name: goclaw
    restart: always
    networks:
      - proxy_net
    expose:
      - "18790"
    environment:
      - GOCLAW_HOST=0.0.0.0
      - GOCLAW_PORT=18790
      - GOCLAW_CONFIG=/app/data/config.json
      - GOCLAW_SKILLS_DIR=/app/data/skills
      - GOCLAW_ALLOW_INSECURE_NO_AUTH=0
      - GOCLAW_GATEWAY_TOKEN=2d75aad76505df8c3cb0077263f04a7f4912f183f08a114831d7f30acb3c82e0
      - GOCLAW_ENCRYPTION_KEY=7f648fc45bef1f1b9a2422f116e3deab1e35030ebbf9fd6a80a9e7f3a0171368
      - GOCLAW_POSTGRES_DSN=postgres://goclaw_user:a2983158cae75314cddd5d6a0d421745@postgres:5432/goclaw?sslmode=disable
    volumes:
      - ./goclaw/data:/app/data
      - ./goclaw/workspace:/app/workspace
```

---

## 📡 Ingress & DNS Configuration

### 1. Pi 5 Gateway Routing (Caddy)
The Caddy routing rule in `/ssd-data/infra/Caddyfile` proxies requests directly to the container using Docker DNS resolution:
```caddy
    @goclaw host goclaw.dungxbuif.com
    handle @goclaw {
        reverse_proxy goclaw:18790
    }
```
Reload Caddy:
```bash
cd /ssd-data/infra && docker compose exec -w /etc/caddy caddy caddy reload
```

### 2. DNS Rewrite
No changes are required. The wildcard record `*.dungxbuif.com -> 10.10.0.5` in AdGuard Home automatically routes requests to the Pi 5.

---

## 🔧 Troubleshooting & Resolved Issues

### 1. Missing `pgvector` Extension in PostgreSQL
*   **Symptom**: Migration 1 (`000001_init_schema.up.sql`) crashed with `pq: extension "vector" is not available`.
*   **Resolution**: Switched the Postgres image on the Pi 5 to `pgvector/pgvector:pg16` in `docker-compose.yml`. Refreshed glibc collations (`ALTER DATABASE template1 REFRESH COLLATION VERSION;`) and enabled the extension.

### 2. File Permissions in Docker Volume
*   **Symptom**: Permission denied errors when GoClaw tries to write to `/app/data/`.
*   **Resolution**: Created `/ssd-data/infra/goclaw/data` and `workspace` directories on the host under the `dungxbuif` user (UID 1000) prior to starting the container. This matches the container's non-root `goclaw` user (UID 1000) and enables full write privileges.

### 3. Headless Browser Failure (go-rod / Chromium)
*   **Symptom**: Agent browser tool calls fail with `failed to start browser: launch Chrome: can't find a browser binary for your OS... Not able to find a valid URL to download...`.
*   **Root Cause**: Even when the `chromium` package is pre-installed via Alpine's package manager in `Dockerfile`, `go-rod`'s default behavior when calling `launcher.New()` is to always attempt to download a statically-versioned Chromium binary if `.Bin(path)` is not explicitly set on the launcher. Inside isolated container networks or unsupported OS/architectures (e.g. ARM64 Alpine), this download fails.
*   **Resolution**: 
    1.  **Dockerfile**: Installed the official Alpine `chromium` package (`apk add --no-cache chromium`) in the runtime stage.
    2.  **GoClaw Source (Binary Path)**: Modified `pkg/browser/browser.go` on Pi 5 to search for the system binary using `launcher.LookPath()` and pass it explicitly using `launcher.New().Bin(binPath)` if found. This prevents `go-rod` from attempting to download external binaries.
    3.  **Sandbox Isolation**: Added the `--no-sandbox` flag to the browser launcher chain in `pkg/browser/browser.go` (via `Set("no-sandbox")`) to prevent Chromium from crashing due to default Docker seccomp sandbox security policies (`Failed to move to new namespace`).
    4.  **Context Leak & Reconnection Fix**: Refactored `Start(ctx)` in `pkg/browser/browser.go`. Previously, the base `rod.Browser` instance was initialized with `connectCtx` (which had a short-lived timeout and was immediately canceled when `Start()` returned via deferred `connectCancel()`). Consequently, subsequent tool invocations failed with `context canceled`. Attempting to connect with a cloned context (`b.Context(connectCtx).Connect()`) left the main instance's connection uninitialized, leading to a nil pointer dereference panic. We resolved this by initializing the connection with the timeout context directly (`b := rod.New().Context(connectCtx)`), calling `.Connect()`, and then cloning it to a persistent background context (`m.browser = b.Context(context.Background())`) to keep the active connection alive and reusable.

---

## 🔄 How to Pull Upstream Updates
When updating GoClaw to the latest upstream version while preserving local `Dockerfile` modifications:
1. SSH into the Pi 5:
   ```bash
   ssh 10.10.0.5
   ```
2. Navigate to the GoClaw repository directory:
   ```bash
   cd /ssd-data/goclaw
   ```
3. Stash local modifications, pull updates, and pop the stash:
   ```bash
   git stash
   git pull
   git stash pop
   ```
4. Rebuild and restart the container:
   ```bash
   cd /ssd-data/infra
   docker compose build goclaw
   docker compose up -d goclaw
   ```