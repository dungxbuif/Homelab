# VM100 Remaining Routing Cutovers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move MezonHook, Family Tree, and macocr-proxy to portless Swarm routes, then normalize avoidable Pi5 database/Redis IP dependencies without altering data or application code.

**Architecture:** Pi5 remains manager/datastore, VM100 remains compute, and Orange Pi remains the file-provider Traefik edge. For each app, create a VM100-constrained one-replica service beside Compose, probe `tasks.<service>` from Orange Pi, change only its file route, verify both the app and cross-route probes over time, then stop only its old Compose container. Preserve source/mounts/secrets and Compose rollback. Existing edge overlay 502 behavior must be actively monitored; if it recurs, capture boundaries before attempting recovery.

**Tech Stack:** Docker Swarm, `homelab-net`, Traefik 3.6 file provider, VM100 Compose, Pi5 PostgreSQL/PgBouncer/Redis.

**Spec:** `docs/superpowers/specs/2026-09-15-swarm-routing-normalization-design.md`

## Global Constraints

- Prefix shell commands with `rtk`; use `apply_patch` for local manual edits. Do not print credentials or repair malformed `local_vars.json`.
- Preserve all unrelated dirty/untracked worktree files; stage only newly owned deployment notes/plans.
- No new published app or DB ports, no `traefik.*` labels or Swarm provider, no database reset/move, and no change to Mac native OCR/LM Studio endpoints.
- Before each service update, capture image ID, Compose project, environment keys, mounts, healthcheck, public status, and source/live Traefik hashes. Ensure the Swarm service name is absent.
- Probe each canary from the **existing Traefik task network namespace** on
  Orange Pi (`docker run --network container:<traefik-cid> ...`) and verify
  VM100 overlay membership. Do not create a fresh attachable overlay endpoint
  on Orange Pi during production cutovers: three earlier cross-route 502
  events followed that diagnostic pattern, whereas the OCR VM100 service join
  and shared-namespace probe left routes healthy. This is a working risk
  reduction hypothesis, not a proven Docker root cause. Run at least four
  public probe rounds 15s apart plus a 10-minute check before stopping each
  old container. Probe Homepage/n8n and at least one Pi5 route as controls.
- If several overlay routes return 502, stop the cutover, preserve evidence, and recover the edge task only after identifying the failing boundary; do not interpret the app route as the sole cause.

## Observed Edge Recovery During Task 1

Adding the MezonHook canary at about 13:37 UTC coincided with Homepage,
n8n, and pgAdmin returning 502 while MezonHook still returned 200 through its
old LAN route. Before any MezonHook route edit, a curl container sharing the
existing Traefik task's network namespace failed to connect to
`tasks.homepage:80` (~3 seconds); `/proc/net/arp` there showed overlay
destinations with `Flags 0x0` and empty MAC addresses. A fresh Orange Pi
container on `homelab-net` reached Homepage with HTTP 200 and a resolved
`Flags 0x2` ARP entry. Replacing only `edge_traefik` made the shared-namespace
probe return 200 with resolved ARP and restored public routes. This localizes
the failure to the old edge task's overlay endpoint/network namespace; the
kernel/Docker mechanism that causes the entries to become unresolved still
needs investigation. Before each next service creation or update, check
cross-route health; if the same failure recurs, collect the paired probes and
ARP state before a controlled edge task replacement.

---

### Task 1: MezonHook

**Files:** `migration/traefik/dynamic.yml`, `docs/VM100.md`, `docs/MAIN.md`, `docs/LOG.md`, `migration/README.md`, new `docs/deployments/mezonhook-2026-09-15.md`.

**Interfaces:** Old Compose project `mezonhook`, container `vm100-mezonhook`, image `homelab/mezonhook:vm100-20260911` (ID `sha256:9f2bcbce8bcb5c73ac44d1f79445129eabae9b9d356f9b3a4960f401e0f8e497`), health command `wget -qO- --timeout=3 http://127.0.0.1:8080/`, old route `10.10.0.31:18084`. New service `mezonhook`, target `tasks.mezonhook:8080`.

- [x] Capture baseline route/hash and confirm service name absent, public `200`, Compose container healthy.
- [x] Create a one-replica VM100-constrained service from the exact current image on `homelab-net`, no ports/mounts, with Compose-equivalent healthcheck.
- [x] Probe task DNS/TCP/HTTP from Orange Pi; inspect VM100 task image ID, placement, and health.
- [x] Prove route assertion fails before edit, patch only MezonHook upstream, parse YAML, backup/sync into live dynamic file, verify source/live SHA256.
- [x] Probe MezonHook + Homepage + n8n + Pi5 overlay route four times at least 15s apart, inspect edge logs, and repeat after 10 minutes.
- [x] Stop only `docker compose -p mezonhook -f /opt/apps/mezonhook/run/docker-compose.yml stop mezonhook`; verify `18084` closed and public routes still pass. Retain Compose and image for rollback.
- [x] Reconcile docs and write deployment note with exact hashes, backup, probe outcomes, incident observations, and rollback.

### Task 2: Family Tree

**Files:** same route/topology/runbook docs and new `docs/deployments/family-tree-2026-09-15.md`.

**Interfaces:** Old Compose project `family_tree`, service `app`, container
`vm100-family-tree-app`; image `oven/bun:1-slim` (VM100 image ID
`sha256:cb3bbbb08e13a4a2ff400f24c7a2a1d5efa83f6ef8544d52d95a519631e2fc61`),
command `bun run start` from `/app`, port `18085:3000`, 18 environment
entries, VM100 bind mounts `/opt/apps/family-tree/src:/app` and
`/opt/apps/family-tree/uploads:/app/uploads` (uploads mode 700), health
`bun -e` fetch of `http://127.0.0.1:3000/login` with 15s start period.
New service `family-tree`, target `tasks.family-tree:3000`.

- [x] Inspect exact Compose project, image digest, command, env keys, user/workdir, mounts, healthcheck, and data read/write behavior without printing secrets.
- [x] Create VM100-constrained service with identical mounts/command/env/health; leave old runtime running and verify task readiness plus a real Family Tree read path.
- [x] Change only Family Tree file route after Orange Pi task probe; backup/sync and verify source/live hashes.
- [x] Run four timed public/cross-route probe rounds and a 10-minute check; stop only its old Compose service if stable, verify `18085` closed and uploads persist.
- [x] Reconcile docs and write deployment note with rollback.

### Task 3: macocr-proxy

**Files:** same route/topology/runbook docs and new `docs/deployments/macocr-proxy-2026-09-15.md`.

**Interfaces:** Old Compose project `macocr_proxy`, service `macocr-proxy`,
container `vm100-macocr-proxy`; image
`homelab/macocr-proxy:vm100-20260910` (VM100 image ID
`sha256:6e99e8d01657e536f4276de4faec1acc55102988ed41bf6e511ac378417b0d0c`),
19 environment entries, no mounts, health `wget -qO- --timeout=3
http://localhost:8080/healthz`, port `18080:8080`. New service
`macocr-proxy`, target `tasks.macocr-proxy:8080`; native Mac OCR
`10.10.0.6:8787` stays a LAN exception.

- [x] Inspect exact image, Compose project, environment/mounts/health, and OCR request flow without printing secrets.
- [x] Create VM100-constrained portless service with identical configuration; probe `/healthz` from the existing Orange Pi Traefik network namespace and `/capacity` from the VM100 task namespace. Do not submit an OCR job with user data merely for a migration check.
- [x] Change only OCR file route; backup/sync and verify hashes, four timed public/cross-route rounds, and a 10-minute check.
- [x] Stop only its old Compose service after stability/native checks, verify `18080` closed and OCR public health/docs work; reconcile docs and deployment note. Redis AUTH directly from the task namespace returns `PONG`; `redis-cli -u` reported a misleading URL-auth failure for both old and new containers.

### Task 4: Pi5 Datastore Endpoints

**Files:** `docs/PI.md`, `docs/VM100.md`, `docs/MAIN.md`, `docs/LOG.md`, and per-client deployment notes.

- [x] Capture redacted specs/rollback values and test authenticated `pgbouncer:6432` DB read from `homelab-net`; inspect PgBouncer transaction/session behavior and app compatibility. Existing session-mode pooler remains for app clients; GitLab uses direct `postgres:5432`.
- [x] Update PostgreSQL clients n8n, Family Tree, and macocr-proxy one at a time to `pgbouncer:6432`, preserving DB/user/password/TLS and verifying private `SELECT 1`, task health, and public flow. The operator later approved MyPocket inclusion; API and worker updates remain below.
- [x] Inspect Pi5 `redis-prod` internal port, auth/AOF/persistence, clients, and overlay attachment. Install secret-free Compose override retaining its default bridge plus external `homelab-net` alias `redis-prod`; verify merged config, controlled recreate, authenticated `PONG`, same `/data` bind, and AOF after restart.
- [x] Update macocr-proxy Redis endpoint to `redis-prod:6379/0` after authenticated overlay probe. The operator later approved MyPocket API/worker Redis DNS updates; no data reset or port closure.
- [x] After Pi5 shared Redis 1 GiB/`noeviction` and 4 GiB swap are active, move MyPocket API DB/Redis URLs, verify; then worker DB/Redis URLs, verify. Preserve all credentials, database names, Redis DB indexes, and app code; rollback only a failing service. Both task namespaces passed `SELECT 1`/`PONG`; API healthy, worker ready, public money 200.
- [x] Audit active route targets, service labels, env IPs, host listeners, source/live config, and public app smoke probes. Ten approved public app paths returned 200; no VM100 datastore IP literals remain. Documented Mac-native and OpenClaw security exceptions, Pi5 monitoring/RelayHub test binds, and GitLab public 404 pending ingress.

### Task 5: Post-Cutover Network Review

**Files:** `docs/MAIN.md`, `docs/VM100.md`, `docs/PI.md`, `migration/README.md`, new network-membership audit note under `docs/research/`.

- [x] Inventory VM100/Pi5/Orange Pi service memberships, published ports, and redacted hardcoded-IP env/route values; app-to-app calls not exercised without test payloads are labeled unverified in the audit note.
- [x] Build a connection matrix from route/config evidence and verified DB/Redis/native probes; BDS cloudflared remains only on `bds-tunnel-net`.
- [x] Identify private overlay candidates for ingress, datastore, worker/app, and edge transport in `docs/research/network-segmentation-2026-09-15.md`.
- [x] Apply only the narrowly verified Redis overlay join needed for OCR DNS. Leave broad Swarm segmentation as a recommendation requiring explicit design approval and per-app rollback tests; no other production network joins/removals were made.

### Task 6: GitLab VM100 Deployment (after network review and operator preflight)

**Files:** `docs/research/gitlab-vm100-preflight-2026-09-15.md`, `migration/traefik/dynamic.yml`, `migration/README.md`, `docs/VM100.md`, `docs/PI.md`, `docs/MAIN.md`, `docs/LOG.md`, new GitLab deployment note and VM100 runtime config.

- [x] VM100 NVMe disk is expanded to 200G, post-restart Discard is active and host thin-pool TRIM reclaimed space. Pi5 GitLab DB/role/extensions, shared Redis 1 GiB/`noeviction`, and exact pinned CE 18.11.11 compatibility with Pi5 PG16 were confirmed. Public SSH TCP ingress remains below.
- [x] Deploy one persistent GitLab service on VM100 with direct private `postgres:5432`, shared `redis-prod:6379/2`, local SSD Gitaly data, and no HTTP host port; configure secrets outside git. Internal login/SSH and second `gitlab:check` passed after isolated Gitaly restart.
- [ ] Verify GitLab readiness, user/repository creation, HTTPS clone/push/pull, backup/restore method, and memory/disk/DB/Redis health before public routing. Internal readiness and initial capacity sample are done; repository flow and off-host backup/restore are not yet verified.
- [ ] Add `gitlab.dungxbuif.com` file route/VPS allow-list and the operator-requested public Git-over-SSH TCP ingress; test public behavior and record rollback.
- [ ] Optionally enable RustFS S3 only after presigned/multipart/ETag compatibility tests, with separate object-type and backup/registry handling.
