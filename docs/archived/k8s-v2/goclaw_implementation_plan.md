---
type: Playbook
title: "GoClaw Deployment & Hardening Plan"
description: "Comprehensive deployment steps for GoClaw on HA Kubernetes, covering database user isolation and PgBouncer integration"
timestamp: 2026-07-03T15:14:00Z
---

# GoClaw Local Docker Deployment & K8s Deprecation Plan

This plan documents the architectural decision to deprecate the Kubernetes-based deployment of GoClaw (`nextlevelbuilder/goclaw`) and transition to a local Docker deployment directly on the Raspberry Pi 5.

---

## 📂 Deployment Strategy Shift & Rationale

Initially, GoClaw was scheduled to deploy on the HA Kubernetes cluster using Longhorn PVCs and Caddy forwarding. During implementation, several issues were encountered:
1.  **PgBouncer advisory lock mismatch**: GoClaw's migration engine (`golang-migrate`) uses advisory locks which fail under PgBouncer's `transaction` pool mode. Connecting directly to the local Postgres container via Docker's internal network (`proxy_net`) bypasses this entirely.
2.  **Longhorn PVC write permissions**: Kubernetes mounts PVCs as `root:root` by default, which required additional `securityContext` tuning to allow GoClaw (running as UID 1000) to write configuration files.
3.  **Local Resource Isolation**: GoClaw runs resource-heavy autonomous agent tasks (Claude Code). Moving it to Docker on the Pi 5 isolates the agent execution environment, preventing K8s node CPU/memory exhaustion.

Therefore, the K8s manifests have been temporarily moved to the **`deprecated`** directory, and GoClaw is running as a local container on the Pi 5.

---

## 📂 Deprecated Resources

The original K8s IaC configuration files have been moved to:
*   [deprecated/goclaw-k8s/](file:///Users/dungxbuif/workspace/Homelab/deprecated/goclaw-k8s/)
    *   `ns.yaml` - K8s Namespace
    *   `pvc.yaml` - Longhorn PVC
    *   `deployment.yaml` - K8s Deployment
    *   `service.yaml` - K8s Service
    *   `ingressroute.yaml` - Traefik IngressRoute
    *   `argocd-app.yaml` - ArgoCD App definition
    *   `provision.sh` - K8s Provisioning script

---

## 🛠️ New Docker Deploy Strategy (Pi 5)

GoClaw is now deployed directly inside the Pi 5's `/ssd-data/infra/docker-compose.yml` configuration:

### 1. Compose Configuration
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

### 2. Caddy Ingress Configuration
Caddy on the Pi 5 maps the domain to the local container via internal Docker DNS:
```caddy
    @goclaw host goclaw.dungxbuif.com
    handle @goclaw {
        reverse_proxy goclaw:18790
    }
```

---

## 🏁 Verification Status

1.  **Container Status**: GoClaw is running on Pi 5 (exposed internally on `18790` inside `proxy_net`).
2.  **DNS & Routing**: Wildcard rewrite `*.dungxbuif.com -> 10.10.0.5` is active and Caddy routes requests correctly.
3.  **Logs verification**: DB schema successfully migrated to version 80, Telegram bot is polling, and embedded Web UI is active.