# Homepage Swarm Cutover Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the VM100 homepage from a published Compose host port to a portless Swarm service without changing its public domains or content.

**Architecture:** Run a second homepage instance on VM100 as service `homepage` on `homelab-net`. Probe it through `tasks.homepage:80`, switch only the Orange Pi file route, keep the old Compose container during stability checks, then stop it. The file provider remains the only active Traefik provider.

**Tech Stack:** Docker 29 / Swarm overlay, `homelab/homepage:vm100-20260910`, Traefik 3.6 file provider, Nginx runtime.

**Spec:** `docs/superpowers/specs/2026-09-15-swarm-routing-normalization-design.md`

## Global Constraints

- Pi5 remains the Swarm manager/datastore; VM100 (`vm100-prod`) is the only homepage compute node; Orange Pi remains the edge worker.
- No new homepage host port. Do not enable Traefik's Swarm provider or Docker socket proxy; do not add inert `traefik.*` labels.
- Preserve `dungxbuif.com` and `www.dungxbuif.com`, the VPS HostSNI allow-list, image tag, and the existing Compose rollback files.
- No database, Redis, MyPocket, BDS, or NetBird changes in this task.
- Preserve existing unrelated worktree changes. Use `apply_patch` for manual local edits and prefix shell commands with `rtk`.

---

### Task 1: Homepage Canary And Route Cutover

**Files:**
- Modify: `migration/traefik/dynamic.yml` (homepage upstream only)
- Modify: `docs/VM100.md`, `docs/MAIN.md`, `docs/LOG.md`, `migration/README.md` (deployed state)
- Create: `docs/deployments/homepage-2026-09-15.md` (canary, cutover, rollback evidence)
- Runtime: VM100 `/opt/apps/homepage/run/docker-compose.yml`; Orange Pi `/opt/edge/traefik/dynamic.yml`; Pi5 Swarm service `homepage`

**Interfaces:**
- Consumes: `homelab-net`, VM100-local `homelab/homepage:vm100-20260910`, current public route to `10.10.0.31:18081`
- Produces: `homepage` one-replica Swarm service on VM100 and `homepage@file` target `http://tasks.homepage:80`

- [x] **Step 1: Capture baseline and confirm no name collision**

Run read-only checks from authenticated Pi5 manager, VM100, and Orange Pi:

```sh
docker service inspect homepage >/dev/null 2>&1 && exit 1 || true
docker node ls --format '{{.Hostname}} {{.Status}} {{.Availability}}'
docker image inspect homelab/homepage:vm100-20260910 --format '{{.Id}}'
docker compose -f /opt/apps/homepage/run/docker-compose.yml ps
sha256sum /opt/edge/traefik/dynamic.yml
curl -sk --resolve dungxbuif.com:443:103.82.21.202 -o /dev/null -w '%{http_code}\n' https://dungxbuif.com/
```

The first two commands run on Pi5; the next two on VM100; the SHA256 check on Orange Pi; curl from the local workspace. Also record `rtk shasum -a 256 migration/traefik/dynamic.yml` before the source edit. Expected: no `homepage` Swarm service; VM100 image and Compose container exist; public `200`; pre-edit source and live dynamic YAML hashes match. Use authenticated SSH sessions; do not place credentials in the plan or repo.

- [x] **Step 2: Create the portless canary**

On the Pi5 manager:

```sh
docker service create \
  --name homepage \
  --replicas 1 \
  --constraint 'node.hostname==vm100-prod' \
  --network homelab-net \
  --health-cmd 'wget -qO- --timeout=3 http://localhost:80/' \
  --health-interval 30s \
  --health-timeout 5s \
  --health-retries 3 \
  homelab/homepage:vm100-20260910
docker service ps homepage --filter desired-state=running
```

Expected: one running task on `vm100-prod`; no published port; task health becomes `healthy`. The image itself has no healthcheck; these flags reproduce the existing Compose healthcheck. The initial 2026-09-15 canary was created without those flags before this difference was found; verify `health=none` as the failing assertion, then apply the same four flags with `docker service update` to correct that unrouted canary before Step 3.

- [x] **Step 3: Probe the canary before routing**

On Orange Pi:

```sh
docker run --rm --network homelab-net curlimages/curl:8.11.1 \
  -fsS --max-time 10 -o /dev/null -w '%{http_code}\n' \
  http://tasks.homepage:80/
```

Expected: `200`. On VM100, inspect the new task's image, overlay network, and health status. Do not edit the public route unless the canary responds and the task stays healthy.

- [x] **Step 4: Prove the source route assertion fails, then edit it**

In the repo, run `rtk rg -q 'url: http://tasks.homepage:80' migration/traefik/dynamic.yml`; it must fail before the edit. Apply a one-line patch to the `homepage` service URL, changing `http://10.10.0.31:18081` to `http://tasks.homepage:80`. Re-run the same assertion; it must pass. Parse the YAML with `rtk proxy docker run --rm -v "$PWD/migration/traefik:/work:ro" mikefarah/yq:4 eval '.' /work/dynamic.yml` and run `rtk git diff --check`.

- [x] **Step 5: Backup and sync the Orange Pi file route**

Before syncing, confirm the live dynamic YAML equals the pre-edit repository hash captured in Step 1. Use these commands with the Orange Pi SSH key from `credentials/id_homelab_k8s`:

```sh
ssh dungxbuif@10.10.0.2 'stamp=$(date +%Y%m%d-%H%M%S); cp /opt/edge/traefik/dynamic.yml /opt/edge/traefik/dynamic.yml.bak-homepage-swarm-$stamp; echo "$stamp"'
scp migration/traefik/dynamic.yml dungxbuif@10.10.0.2:/tmp/homepage-dynamic.yml
ssh dungxbuif@10.10.0.2 'cp /tmp/homepage-dynamic.yml /opt/edge/traefik/dynamic.yml; sha256sum /opt/edge/traefik/dynamic.yml'
```

Copy **into the existing** live file so file-provider watch can reload without replacing the bind mount. Confirm live/source SHA256 equality and `homepage@file` access logs point to `tasks.homepage:80`. Do not restart Traefik unless reload verification fails.

- [x] **Step 6: Verify public behavior and retain the old container during stability checks**

Probe `dungxbuif.com`, `www.dungxbuif.com`, and n8n through the VPS; each must return `200`:

```sh
for host in dungxbuif.com www.dungxbuif.com n8n.dungxbuif.com; do
  curl -sk --resolve "$host:443:103.82.21.202" -o /dev/null -w "$host %{http_code}\n" --max-time 12 "https://$host/"
done
```

Run four rounds at least 15 seconds apart, inspect Orange Pi Traefik logs for `502` or overlay errors, then probe again at least 10 minutes after cutover. Keep `vm100-homepage` running throughout this period as rollback. If the changed route fails, restore the saved dynamic YAML immediately; do not change other routers.

- [x] **Step 7: Retire only the old Compose runtime and reconcile docs**

After Step 6 passes, on VM100 run:

```sh
docker compose -f /opt/apps/homepage/run/docker-compose.yml stop homepage
docker ps --filter name=vm100-homepage --format '{{.Names}} {{.Status}}'
```

Expected: old container stopped, no listener on `18081`, Swarm `homepage` remains healthy, public domains remain `200`. Keep Compose YAML and local image for rollback; if needed, restore the old file route and run `docker compose -f /opt/apps/homepage/run/docker-compose.yml start homepage`.

Update `docs/VM100.md`, `docs/MAIN.md`, `docs/LOG.md`, and `migration/README.md` to show `homepage` on Swarm and `tasks.homepage:80`. Recheck source/live config equality and run `rtk git diff --check`. The public hostname list and Markdown route catalog remain the AI-readable reference; no homepage API contract changes.

- [x] **Step 8: Record evidence and commit only new owned files**

Write `docs/deployments/homepage-2026-09-15.md` with the image, Swarm service placement, live/source hashes, backup filename, cutover time, public probes, and rollback command. Stage only that new note and this plan, inspect `rtk git diff --cached --name-only`, then commit with `rtk git commit -m 'docs: record homepage Swarm cutover'`. The current route file and several docs were already untracked/dirty before this task; leave their modifications unstaged and report them rather than committing unrelated prior work.
