# Swarm Routing And Endpoint Normalization Design

**Goal:** Make VM100 production apps use one stable Swarm-overlay routing pattern, remove avoidable Pi5 IP dependencies, and document which labels actually affect routing.

## Current Baseline (2026-09-15)

- Pi5 is the Swarm manager and datastore host; VM100 is the production worker; Orange Pi is the edge worker.
- Orange Pi Traefik has only the file provider enabled. Its source and live static/dynamic YAML have matching SHA256 hashes. No `traefik.*` service label creates a route in this runtime.
- Existing portless Swarm apps route through `tasks.<service>` DNS on `homelab-net`: OpenClaw, n8n, MyPocket, NetBird, and RelayHub. Pi5 HTTP backends use container names on the same overlay.
- Homepage, macocr-proxy, MezonHook, and Family Tree are standalone VM100 Compose containers on separate bridge networks. Orange Pi routes to VM100 host ports `18081`, `18080`, `18084`, and `18085`, respectively.
- The Mac-native LM Studio (`10.10.0.6:1234`) and OCR (`10.10.0.6:8787`) remain LAN dependencies, not Swarm candidates.
- n8n uses Pi5 `10.10.0.5:5432` for PostgreSQL. MyPocket API/worker use the same PostgreSQL endpoint and Pi5 Redis at `10.10.0.5:16379`. Family Tree and macocr-proxy also use Pi5 LAN datastore endpoints.
- From `homelab-net` on VM100, `postgres:5432` and `pgbouncer:6432` resolve and accept TCP connections. `redis-prod` does not currently resolve on the overlay.
- NetBird's `reverseProxy.trustedHTTPProxies` contains `172.30.0.10/32`; that is a trust rule, not an upstream. It does not match the current Traefik task or service VIP, so it needs a separate security review.
- Pi5 manager service-label inventory was not available during this audit: the local `local_vars.json` is not parseable, key-based SSH failed, and the 1Password SSH agent did not complete authentication. Manager access is a deployment prerequisite, not a reason to guess credentials.

## Decision And Label Policy

Keep the Orange Pi Traefik **file provider** as the sole active routing source. All new portless Swarm HTTP services on `homelab-net` get file routes to `http://tasks.<service>:<container-port>` (or `h2c://` where the protocol requires it). Preserve the exact public hostnames and the VPS HostSNI allow-list. Do not restore the experimental manager-side Docker socket proxy or Swarm provider; that path caused intermittent overlay reachability and public `502` responses.

`node.labels.edge=true` remains a placement label for the Orange Pi edge stack. VM100 app services use a VM100 placement constraint and remain on `homelab-net`. Do not add `traefik.*` labels as if they were active. After manager access is restored, inspect existing service labels and remove only obsolete Traefik routing labels; preserve placement, stack, and unrelated operational labels. A future automatic label-to-route registrar is a separate design and is not part of this cutover.

## Rollout

### 0. Access And Baseline

- Restore authenticated Pi5 manager access through an existing secure channel. Inspect service specs, labels, replicas, networks, endpoint modes, and current datastore/container placement with read-only commands before any service update.
- Capture redacted service specifications, Compose files, Traefik YAML, image IDs, mounts, and baseline public/internal probes. Keep secret-bearing rollback material off git with restrictive permissions.
- Do not repair `local_vars.json` by reconstructing or printing secrets; credential recovery is a separate explicit action.

### 1. VM100 HTTP Services

Move one app at a time into a new one-replica Swarm service constrained to VM100 and attached to `homelab-net`, with no published host port. Use the current runtime image, environment, healthcheck, and data mounts. Start the Swarm service beside the existing Compose container, probe `tasks.<service>` internally from Orange Pi, then change only that app's file route. Verify public behavior before stopping the old container. Retain the Compose config and image for rollback until a later cleanup window.

Cutover order and intended service names:

| Current Compose container | New Swarm service | File target after cutover |
|---|---|---|
| `vm100-homepage` | `homepage` | `http://tasks.homepage:80` |
| `vm100-mezonhook` | `mezonhook` | `http://tasks.mezonhook:8080` |
| `vm100-family-tree-app` | `family-tree` | `http://tasks.family-tree:3000` |
| `vm100-macocr-proxy` | `macocr-proxy` | `http://tasks.macocr-proxy:8080` |

Confirm none of these service names is already in use during the manager inventory. Family Tree keeps the VM100 source and uploads bind mounts, so its service must stay on that node. Mac OCR continues to call the native Mac OCR endpoint over LAN; that exception must not be disguised as Docker DNS. Remove the old VM100 host-port listener only after the file route and health checks are stable.

### 2. PostgreSQL Clients

After each client is on `homelab-net`, replace the published Pi5 PgBouncer endpoint `10.10.0.5:5432` with the internal `pgbouncer:6432` endpoint, preserving database, user, password, TLS, and pool behavior. Scope this to n8n, MyPocket API/worker, Family Tree, and macocr-proxy. Update one client at a time and verify application readiness plus a real read operation; TCP reachability alone is not enough. Do not reset, recreate, expose, or migrate any database.

### 3. Redis Clients

Keep `10.10.0.5:16379` until the Pi5 Redis container's current internal port, authentication, persistence, and client inventory are verified on the manager. If the existing standalone Redis can safely join the attachable `homelab-net`, connect it with a stable `redis-prod` DNS alias, test authenticated commands from VM100, and then migrate MyPocket API/worker and macocr-proxy one at a time. If overlay attachment or auth verification fails, leave these clients on the documented LAN exception rather than forcing a DNS change. Preserve the LAN endpoint for other confirmed clients. No Redis data reset or port closure is authorized by this design.

## Security Exception: NetBird Proxy Trust

Do not replace `172.30.0.10/32` with another task IP or a blanket `172.30.0.0/16` range. The source address seen by NetBird and its forwarded-header chain must be captured first, and the proxy trust boundary reviewed independently. A security-specific follow-up can choose a dedicated ingress network, a narrowly trusted address policy, or a verified trusted-hop setting. This routing cutover only records the drift; it does not change NetBird authentication/proxy trust in production.

## Rollback And Verification

**Operational probe amendment (2026-09-15):** During Homepage, MezonHook, and
Family Tree canaries, newly attached Orange Pi overlay curl helpers were
followed by the long-lived Traefik task losing ARP resolution for multiple
overlay destinations; a fresh helper could still connect, and replacing the
Traefik task restored it. The OCR canary joined on VM100 and was reachable
from a helper sharing the existing Traefik network namespace without creating
a new Orange Pi overlay member; cross-route probes remained healthy. For
remaining production cutovers, probe from the existing edge task's network
namespace (and inspect VM100 service membership) rather than joining a new
attachable Orange Pi container to `homelab-net`. This changes the diagnostic
method, not the file-provider routing architecture. The causal trigger and
Docker/kernel mechanism remain unconfirmed.

- Every app has a single-router cutover: restore that router's previous VM100 host-port target if its Swarm canary or public probe fails, then keep or restart the existing Compose container. Do not roll back other applications as a group.
- For a datastore URL regression, restore only that client's prior endpoint from its captured spec; preserve credentials and data.
- Verify `tasks.<service>` DNS and container-port connectivity from Orange Pi and VM100, Swarm replica placement on VM100, zero app host ports after each finalized cutover, and source/live Traefik config equality.
- Public smoke probes must cover homepage, OCR, MezonHook, Family Tree, money, n8n, OpenClaw, RelayHub health, and NetBird. Auth/bootstrapping responses such as OpenClaw `403` and RelayHub `/readyz 503` are expected, not proxy failures.
- Inspect Traefik access/error logs for `502`, overlay reachability errors, and correct `@file` router names after each cutover. Probe the changed domain and n8n four times at least 15 seconds apart, then check again after at least 10 minutes before retiring the old Compose container. Do not claim success from one successful curl.

## Documentation And Boundaries

- Update `migration/traefik/dynamic.yml`, `migration/README.md`, `docs/VM100.md`, `docs/PI.md`, `docs/MAIN.md`, and `docs/LOG.md` as each deployed state changes. Live Orange Pi and VM100 files must match the documented source of truth.
- Keep the user-facing domain list and the structured Markdown route catalog in sync; no API contract or database schema changes are planned.
- Do not migrate Pi5 datastores away from Pi5, move MyPocket's development source, reintroduce GoClaw, or alter BDS Cloudflare Tunnel isolation. Do not publish app or database host ports merely to make DNS work.
