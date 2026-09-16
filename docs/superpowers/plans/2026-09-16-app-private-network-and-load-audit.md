# App Private Network and Load Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split production applications away from the broad `homelab-net` where practical, then measure VM100/Pi5 resources under representative load before applying resource caps.

**Architecture:** Keep `homelab-net` as the shared edge/legacy compatibility network during the migration. Add narrower Swarm overlay networks per traffic class and migrate one application at a time with rollback commands captured before each change. Resource limits are not changed until baseline, load sample, and service-specific recommendations are recorded.

**Tech Stack:** Docker Swarm overlay networks, Orange Pi Traefik file provider, Rathole edge tunnels, Pi5 PostgreSQL/PgBouncer/Redis/RustFS, VM100 Swarm services, `docker stats`, `docker service inspect`, `vmstat`, HTTP and datastore probes.

**Spec:** [Current stack catalog](../../STACK.md), [network segmentation proposal](../../research/network-segmentation-2026-09-15.md), [resource audit](../../research/resource-limit-audit-2026-09-15.md)

## Global Constraints

- Do not remove `homelab-net` from a service until its ingress, datastore, and private east-west probes pass on the replacement network.
- Do not attach `bds-cloudflared` to `homelab-net`; it must remain only on `bds-tunnel-net`.
- Keep Mac native exceptions explicit: OCR may reach `10.10.0.6:8787`; LLM remains development and is not part of this migration.
- Keep GitLab last. It is stateful, public, and currently depends on isolated VPS tunnels plus Pi5 PostgreSQL/Redis.
- Do not change resource limits from idle snapshots alone. Run baseline and a short load sample first, then apply caps one service at a time.
- For every production change, update the relevant deployment/runbook docs and record rollback commands.

---

## Target Network Model

| Network | Members | Purpose |
|---|---|---|
| `homelab-net` | Orange Pi edge, legacy/shared routes during migration, selected Pi5 services until cutover | Compatibility and file-provider routing |
| `edge-http-net` | Orange Pi Traefik plus only HTTP frontends/backends | Public/private HTTP routing surface |
| `data-net` | Pi5 `pgbouncer`, `redis-prod`, selected data consumers | PostgreSQL/Redis application access |
| `gitlab-net` | GitLab Omnibus plus GitLab tunnel clients; optional Pi5 data endpoints if direct DB/Redis can be moved safely | GitLab-specific app/tunnel traffic |
| `mypocket-net` | `mypocket-web`, `mypocket-api`, `mypocket-worker` | MyPocket private service-to-service traffic |
| `netbird-net` | `netbird_netbird-server`, `netbird_netbird-dashboard` | NetBird private app traffic |
| `bds-tunnel-net` | `bds-app`, `bds-cloudflared` | Dedicated Cloudflare connector path; already deployed |

## Files and Docs

- Modify: `docs/research/network-segmentation-2026-09-15.md` with executed state and evidence.
- Modify: `docs/research/resource-limit-audit-2026-09-15.md` with load-sample results and resource recommendations.
- Modify: `docs/STACK.md` after topology changes are actually deployed.
- Modify: service docs under `docs/deployments/` and `docs/services/` only for affected apps.
- Possibly modify: Swarm stack YAML under `migration/` if deployed service specs need durable network definitions.

## Task 1: Fresh Baseline and Rollback Inventory

**Files:**
- Modify: `docs/research/network-segmentation-2026-09-15.md`
- Modify: `docs/research/resource-limit-audit-2026-09-15.md`

**Interfaces:**
- Consumes: current Docker/Swarm state from Pi5, VM100, Orange Pi, and VPS.
- Produces: service/network/resource baseline and per-service rollback commands.

- [ ] **Step 1: Capture Swarm service membership**

Run from a manager:

```bash
docker service ls --format '{{.Name}}'
docker network ls --format '{{.Name}} {{.Driver}} {{.Scope}}'
docker service inspect \
  homepage macocr-proxy family-tree mezonhook openclaw n8n \
  mypocket-web mypocket-api mypocket-worker relayhub \
  gitlab_gitlab gitlab-ssh-tunnel_client gitlab-https-tunnel_client \
  gitlab-registry-trial_client netbird_netbird-server netbird_netbird-dashboard \
  --format '{{.Spec.Name}} {{json .Spec.TaskTemplate.Networks}} {{json .Spec.TaskTemplate.Resources}}'
```

Expected: every inspected service has a current network list and resource spec; missing services are recorded as blockers, not assumed.

- [ ] **Step 2: Capture standalone container membership**

Run on Pi5 and VM100:

```bash
docker ps --format '{{.Names}}'
docker inspect $(docker ps -q) --format '{{.Name}} {{json .NetworkSettings.Networks}} {{json .HostConfig.Memory}} {{json .HostConfig.NanoCpus}}'
```

Expected: Pi5 datastore containers and VM100 `bds-*` containers have explicit network membership recorded.

- [ ] **Step 3: Capture resource baseline**

Run on VM100 and Pi5:

```bash
free -h
df -h /
vmstat 1 5
docker stats --no-stream --format '{{.Name}} {{.CPUPerc}} {{.MemUsage}} {{.MemPerc}} {{.NetIO}} {{.BlockIO}} {{.PIDs}}'
docker ps --format '{{.Names}} {{.Status}}'
```

Expected: record RAM, swap, disk, CPU snapshot, memory snapshot, restart status, and note that this is baseline only.

- [ ] **Step 4: Write rollback commands before network changes**

For each Swarm service, record the current networks and the command form:

```bash
docker service update \
  --network-add homelab-net \
  --network-rm <new-network> \
  <service>
```

Expected: no production service is changed until rollback is written in the research note.

## Task 2: Create Shared Target Overlays

**Files:**
- Modify: `docs/research/network-segmentation-2026-09-15.md`

**Interfaces:**
- Consumes: baseline from Task 1.
- Produces: attachable overlay networks with no service movement yet.

- [ ] **Step 1: Create networks if absent**

Run from Swarm manager:

```bash
docker network create --driver overlay --attachable edge-http-net
docker network create --driver overlay --attachable data-net
docker network create --driver overlay --attachable mypocket-net
docker network create --driver overlay --attachable netbird-net
docker network create --driver overlay --attachable gitlab-net
```

Expected: existing networks are noted; new networks show driver `overlay` and scope `swarm`.

- [ ] **Step 2: Verify DNS and overlay health**

Use a temporary diagnostic container on each new network:

```bash
docker run --rm --network edge-http-net alpine:3.20 getent hosts tasks.homepage
docker run --rm --network data-net alpine:3.20 getent hosts pgbouncer
```

Expected: empty DNS is acceptable before services join; Docker run must start successfully on the manager. If overlay attach fails, stop and investigate before touching services.

## Task 3: Move Low-Risk HTTP Apps First

**Files:**
- Modify: `docs/deployments/homepage-2026-09-15.md`
- Modify: `docs/deployments/family-tree-2026-09-15.md`
- Modify: `docs/deployments/mezonhook-2026-09-15.md`
- Modify: `docs/research/network-segmentation-2026-09-15.md`

**Interfaces:**
- Consumes: `edge-http-net`.
- Produces: Homepage, Family Tree, and MezonHook reachable through edge route and isolated from raw datastore networks where not needed.

- [ ] **Step 1: Attach Traefik and one app to `edge-http-net`**

Start with Homepage:

```bash
docker service update --network-add edge-http-net edge_traefik
docker service update --network-add edge-http-net homepage
```

Expected: both services remain running; `docker service ps` shows new tasks healthy.

- [ ] **Step 2: Verify route and DNS**

Run:

```bash
curl -fsS https://dungxbuif.com/ >/dev/null
docker exec $(docker ps --filter name=edge_traefik -q | head -n1) getent hosts tasks.homepage
```

Expected: public route returns success and Traefik namespace resolves `tasks.homepage`.

- [ ] **Step 3: Remove `homelab-net` only after success**

```bash
docker service update --network-rm homelab-net homepage
```

Expected: `https://dungxbuif.com/` still succeeds after task replacement.

- [ ] **Step 4: Repeat for Family Tree and MezonHook**

Use the same add-verify-remove flow for:

```bash
docker service update --network-add edge-http-net family-tree
docker service update --network-rm homelab-net family-tree
docker service update --network-add edge-http-net mezonhook
docker service update --network-rm homelab-net mezonhook
```

Expected: `family.dungxbuif.com` and `mezonhook.dungxbuif.com` respond after each change.

## Task 4: Move Apps With Datastore Dependencies

**Files:**
- Modify: `docs/deployments/mypocket-dns-migration-2026-09-15.md`
- Modify: `docs/deployments/openclaw-proxy-attribution-2026-09-15.md`
- Modify: `docs/research/network-segmentation-2026-09-15.md`

**Interfaces:**
- Consumes: `edge-http-net`, `data-net`, per-app private networks.
- Produces: MyPocket, n8n, OpenClaw, OCR proxy, and BDS documented with explicit ingress/data/private memberships.

- [ ] **Step 1: Attach Pi5 data services to `data-net`**

On Pi5 Compose or Docker runtime, attach `pgbouncer` and `redis-prod` to `data-net` while preserving current networks:

```bash
docker network connect data-net pgbouncer
docker network connect data-net redis-prod
```

Expected: `pgbouncer` and `redis-prod` retain existing networks and gain `data-net` aliases.

- [ ] **Step 2: Migrate MyPocket as a unit**

```bash
docker service update --network-add edge-http-net --network-add mypocket-net --network-add data-net mypocket-web
docker service update --network-add mypocket-net --network-add data-net mypocket-api
docker service update --network-add mypocket-net --network-add data-net mypocket-worker
```

Expected: API and worker resolve `pgbouncer`/`redis-prod` over Docker DNS; web resolves API according to its current runtime config.

- [ ] **Step 3: Verify MyPocket before removing shared network**

Run task namespace probes:

```bash
getent hosts pgbouncer
getent hosts redis-prod
curl -fsS https://money.dungxbuif.com/ >/dev/null
```

Expected: DNS and public route succeed; worker logs show no repeated DB/Redis errors.

- [ ] **Step 4: Remove `homelab-net` from MyPocket**

```bash
docker service update --network-rm homelab-net mypocket-web
docker service update --network-rm homelab-net mypocket-api
docker service update --network-rm homelab-net mypocket-worker
```

Expected: `money.dungxbuif.com` and DB/Redis probes still pass.

- [ ] **Step 5: Repeat conservative add-verify-remove for n8n, OpenClaw, and OCR**

Add `edge-http-net` to HTTP-facing tasks and `data-net` only where datastore access is required. Keep OCR's Mac LAN dependency documented. Do not remove `homelab-net` if any task still depends on a hostname available only there.

## Task 5: Keep GitLab Separate and Last

**Files:**
- Modify: `docs/services/gitlab.md`
- Modify: `docs/deployments/gitlab-registry-trial-2026-09-16.md`
- Modify: `docs/research/network-segmentation-2026-09-15.md`

**Interfaces:**
- Consumes: stable `data-net` behavior and known GitLab tunnel state.
- Produces: GitLab-specific network design or a documented decision to defer.

- [ ] **Step 1: Test GitLab on added networks only**

```bash
docker service update --network-add gitlab-net --network-add data-net gitlab_gitlab
docker service update --network-add gitlab-net gitlab-ssh-tunnel_client
docker service update --network-add gitlab-net gitlab-https-tunnel_client
docker service update --network-add gitlab-net gitlab-registry-trial_client
```

Expected: GitLab remains healthy; public HTTPS, registry challenge, and SSH banner still work.

- [ ] **Step 2: Decide whether `homelab-net` removal is safe**

Before removal, verify:

```bash
curl -fsS https://gitlab.dungxbuif.com/users/sign_in >/dev/null
curl -fsSI https://registry-gitlab.dungxbuif.com/v2/
ssh -p 2222 -o BatchMode=yes -o StrictHostKeyChecking=accept-new git@gitlab.dungxbuif.com
```

Expected: web and registry respond; SSH reaches GitLab banner or expected Git auth refusal. If edge/LAN split DNS still depends on `homelab-net`, defer removal and document the reason.

## Task 6: Load and Resource Audit

**Files:**
- Modify: `docs/research/resource-limit-audit-2026-09-15.md`
- Modify: `docs/STACK.md`

**Interfaces:**
- Consumes: final network state from Tasks 3-5.
- Produces: service-specific resource recommendations and candidates for limits.

- [ ] **Step 1: Generate representative HTTP load**

For each public HTTP app, run a short, bounded smoke load from a trusted host:

```bash
for url in \
  https://dungxbuif.com/ \
  https://family.dungxbuif.com/ \
  https://mezonhook.dungxbuif.com/ \
  https://n8n.dungxbuif.com/healthz \
  https://openclaw.dungxbuif.com/ \
  https://money.dungxbuif.com/; do
  for i in $(seq 1 30); do curl -fsS "$url" >/dev/null; done
done
```

Expected: no 5xx spike during the short sample. This is not a full stress test.

- [ ] **Step 2: Generate datastore probes under load**

From each data consumer namespace, run one DB/Redis probe using its existing secret/env source. Do not print secret values.

Expected: `SELECT 1` and Redis `PING` pass where applicable.

- [ ] **Step 3: Capture resource sample during and after load**

Run on VM100 and Pi5 during the smoke load and again 2 minutes after:

```bash
docker stats --no-stream --format '{{.Name}} {{.CPUPerc}} {{.MemUsage}} {{.MemPerc}} {{.NetIO}} {{.BlockIO}} {{.PIDs}}'
vmstat 1 5
free -h
```

Expected: record peaks seen in this bounded sample and compare against prior idle samples.

- [ ] **Step 4: Recommend caps, do not apply broad caps automatically**

Document candidate values per service:

```text
homepage: 256 MiB / 0.25 CPU candidate
mezonhook: 256 MiB / 0.25 CPU candidate
macocr-proxy: 512 MiB / 0.5 CPU candidate after upload test
n8n: 1.5-2 GiB / 1 CPU candidate after workflow test
openclaw: 1.5-2 GiB / 1 CPU candidate after provider/device test
gitlab: keep 10 GiB / 4 CPU until real repo/registry/CI workload is measured
```

Expected: docs distinguish measured evidence from recommendations.

## Task 7: Documentation and Git

**Files:**
- Modify: `docs/STACK.md`
- Modify: `docs/research/network-segmentation-2026-09-15.md`
- Modify: `docs/research/resource-limit-audit-2026-09-15.md`
- Modify: affected `docs/deployments/*.md` and `docs/services/*.md`

**Interfaces:**
- Consumes: all verified changes.
- Produces: committed documentation and durable runbook updates.

- [ ] **Step 1: Reconcile current docs**

Update `docs/STACK.md` so `Network and Ingress` describes only deployed state. Keep proposed work clearly marked as proposed.

- [ ] **Step 2: Run docs and repo checks**

```bash
git diff --check
rg -n '10\\.10\\.0\\.(5|31)|homelab-net|edge-http-net|data-net|gitlab-net|mypocket-net|netbird-net' docs migration
```

Expected: IP literals and shared-network references are either intentional exceptions or updated.

- [ ] **Step 3: Commit**

```bash
git add docs migration
git commit -m "docs: record app network segmentation and load audit"
```

Expected: commit includes evidence and no secret values.

## Self-Review

- Spec coverage: covers network split, high-load resource audit, rollback, docs, and app-by-app verification.
- Placeholder scan: no `TBD`, `TODO`, or open-ended “add tests” placeholders.
- Type/name consistency: network names and service names match the current documented stack; live execution must re-check exact service names before commands.

