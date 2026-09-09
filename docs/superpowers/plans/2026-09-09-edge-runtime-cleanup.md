# Edge Runtime Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Orange Pi Traefik the only home-edge implementation, remove retired Caddy/Nginx artifacts and stale routes, and leave PostgreSQL unchanged.

**Architecture:** Capture a recoverable snapshot before any deletion, then make the repository mirror the already-running Orange Pi Traefik deployment. Validate and publish the canonical configuration before removing disabled Caddy resources, old Pi5 edge resources, and VPS Nginx files.

**Tech Stack:** Docker Swarm, Traefik v3.6, Rathole, AdGuard Home, Bash, Python 3 with PyYAML, Markdown.

**Spec:** `docs/superpowers/specs/2026-09-09-edge-cleanup-design.md`

## Global Constraints

- Orange Pi Zero 3 (`10.10.0.2`) remains the home edge and Swarm worker.
- Keep `edge_traefik`, `edge_rathole`, and `edge_adguardhome` active.
- Retire `n8n.dungxbuif.com`, `gitlab.dungxbuif.com`, `git.dungxbuif.com`, and `grafana.dungxbuif.com` from the home edge.
- Do not add, remove, expose, restart, or reconfigure PostgreSQL or a PostgreSQL edge route.
- Never print Cloudflare, Rathole, database, or ACME secrets.
- Keep `/opt/edge/traefik/test-letsencrypt/acme.json` in place as the active production ACME store.
- Preserve pre-existing working-tree changes and stage only files explicitly owned by this plan.

---

### Task 1: Capture Baseline And Rollback Archive

**Files:**
- Create remotely: `/ssd-data/infra/backups/edge-cleanup-20260909/`
- Create remotely: `/ssd-data/infra/backups/edge-cleanup-20260909/swarm-services.json`
- Create remotely: `/ssd-data/infra/backups/edge-cleanup-20260909/orange-edge.tar.gz`
- Create remotely: `/ssd-data/infra/backups/edge-cleanup-20260909/vps-gateway.tar.gz`
- Test: runtime status, archive inventory, PostgreSQL fingerprints

**Interfaces:**
- Consumes: live Docker Swarm service specs and host configuration trees.
- Produces: one Pi5 rollback directory used by every destructive task.

- [ ] **Step 1: Record the current runtime and PostgreSQL baseline without secrets**

Run:

```bash
rtk ssh pi 'docker node inspect orangepizero3 --format "{{.Status.State}} {{.Status.Addr}}"; docker service ls --format "{{.Name}} {{.Replicas}}" | grep ^edge_; docker ps --filter name=postgres --format "{{.Names}} {{.Image}} {{.Status}} {{.Ports}}"'
```

Expected: Orange Pi is `ready`; Traefik, Rathole, and AdGuard are `1/1`; record PostgreSQL output verbatim for Task 7 comparison.

- [ ] **Step 2: Create the protected rollback directory and service snapshot on Pi5**

Run:

```bash
rtk ssh pi 'install -d -m 700 /ssd-data/infra/backups/edge-cleanup-20260909 && docker service inspect edge_traefik edge_rathole edge_adguardhome edge_caddy > /ssd-data/infra/backups/edge-cleanup-20260909/swarm-services.json && chmod 600 /ssd-data/infra/backups/edge-cleanup-20260909/swarm-services.json'
```

Expected: snapshot exists with mode `600`; do not display its contents because service environment values may contain secrets.

- [ ] **Step 3: Archive the complete Orange Pi edge tree, including root-owned certificate data**

Run:

```bash
rtk ssh orange-pi 'docker run --rm -v /home/dungxbuif/edge:/source:ro -v /home/dungxbuif:/backup busybox:1.36.1 tar -czf /backup/orange-edge-20260909.tar.gz -C /source . && chmod 600 /home/dungxbuif/orange-edge-20260909.tar.gz'
rtk scp orange-pi:/home/dungxbuif/orange-edge-20260909.tar.gz /tmp/orange-edge-20260909.tar.gz
rtk scp /tmp/orange-edge-20260909.tar.gz pi:/ssd-data/infra/backups/edge-cleanup-20260909/orange-edge.tar.gz
```

Expected: Pi5 archive contains `caddy/`, `traefik/`, `rathole/`, and `adguard/`; the archive is never committed.

- [ ] **Step 4: Archive VPS gateway configuration without reading secret contents**

Run:

```bash
rtk ssh gateway 'tar -czf /tmp/vps-gateway-20260909.tar.gz -C /root gateway && chmod 600 /tmp/vps-gateway-20260909.tar.gz'
rtk scp gateway:/tmp/vps-gateway-20260909.tar.gz /tmp/vps-gateway-20260909.tar.gz
rtk scp /tmp/vps-gateway-20260909.tar.gz pi:/ssd-data/infra/backups/edge-cleanup-20260909/vps-gateway.tar.gz
```

Expected: all three rollback files exist on Pi5 and have non-zero size.

- [ ] **Step 5: Verify archive integrity before any deletion**

Run:

```bash
rtk ssh pi 'chmod 600 /ssd-data/infra/backups/edge-cleanup-20260909/* && ls -lh /ssd-data/infra/backups/edge-cleanup-20260909 && tar -tzf /ssd-data/infra/backups/edge-cleanup-20260909/orange-edge.tar.gz | grep -E "^\./(caddy|traefik|rathole|adguard)/" | head'
```

Expected: service JSON and both archives are present; archive listing includes all four Orange Pi configuration trees.

---

### Task 2: Establish Canonical Traefik Source In The Repository

**Files:**
- Modify: `migration/edge-stack.yml`
- Create: `migration/traefik/traefik.yml`
- Create: `migration/traefik/dynamic.yml`
- Modify: `migration/README.md`
- Test: stack render, YAML parse, Traefik config validation, route-set comparison

**Interfaces:**
- Consumes: `/opt/edge/traefik/traefik.yml`, `/opt/edge/traefik/dynamic.yml`, and live Swarm specs.
- Produces: secret-free, deployable repository source matching the active Orange Pi edge.

- [ ] **Step 1: Write a failing repository/runtime parity check**

Run:

```bash
rtk test -f migration/traefik/traefik.yml
rtk test -f migration/traefik/dynamic.yml
rtk rg -n 'traefik:v3.6|edge_traefik|service: traefik' migration/edge-stack.yml
```

Expected before implementation: at least one check fails because the repository only defines Caddy.

- [ ] **Step 2: Replace the Caddy service with the live Traefik service definition**

Edit `migration/edge-stack.yml` so it defines Traefik v3.6 on host ports TCP 80, TCP 443, and UDP 443; mounts `/opt/edge/traefik/traefik.yml`, `/opt/edge/traefik/dynamic.yml`, and `/opt/edge/traefik/test-letsencrypt`; reads `CF_DNS_API_TOKEN` from the deploy environment; keeps Rathole and AdGuard; and contains no Caddy service.

- [ ] **Step 3: Add secret-free copies of the active Traefik files**

Create `migration/traefik/traefik.yml` and `migration/traefik/dynamic.yml` from the live Orange Pi files. Preserve all currently active routes and omit retired `n8n`, `gitlab`, `git`, `grafana`, and PostgreSQL routers.

- [ ] **Step 4: Update migration ownership documentation**

Update `migration/README.md` to identify Traefik, Rathole, and AdGuard as the current Orange Pi stack; mark Caddy migration assets as historical rollback material.

- [ ] **Step 5: Validate YAML and Traefik configuration**

Run:

```bash
rtk python3 -c 'import yaml; [yaml.safe_load(open(p)) for p in ["migration/edge-stack.yml", "migration/traefik/traefik.yml", "migration/traefik/dynamic.yml"]]'
rtk docker run --rm -v "$PWD/migration/traefik:/etc/traefik:ro" traefik:v3.6 check-config --configFile=/etc/traefik/traefik.yml
rtk env CF_DNS_API_TOKEN=validation-only docker stack config -c migration/edge-stack.yml >/dev/null
```

Expected: YAML parses, Traefik reports valid static configuration, and Docker renders the stack without exposing the validation value.

- [ ] **Step 6: Commit only canonical stack files**

Run:

```bash
rtk git add migration/edge-stack.yml migration/traefik/traefik.yml migration/traefik/dynamic.yml migration/README.md
rtk git commit -m "infra: make Traefik the canonical home edge"
```

Expected: commit contains no tokens, passwords, ACME JSON, or unrelated working-tree changes.

---

### Task 3: Retarget The Edge Publishing Helper

**Files:**
- Modify: `edge-registrar/scripts/edge-publish.sh`
- Create: `edge-registrar/tests/test-edge-publish.sh`
- Test: dry-run fixture and live dry-run hash check

**Interfaces:**
- Consumes: Orange Pi Traefik `dynamic.yml` and VPS Traefik `dynamic.yml`.
- Produces: idempotent route publishing without any Pi5 Caddy dependency.

- [ ] **Step 1: Add a failing helper test**

Create `edge-registrar/tests/test-edge-publish.sh` with this contract:

```bash
#!/usr/bin/env bash
set -euo pipefail

script="$(cd "$(dirname "$0")/.." && pwd)/scripts/edge-publish.sh"
grep -q 'EDGE_HOST=.*orange-pi' "$script"
grep -q 'EDGE_DYNAMIC_FILE=.*/opt/edge/traefik/dynamic.yml' "$script"
! grep -qE 'PI5_CADDY|/ssd-data/infra/Caddyfile|docker exec.*caddy' "$script"

before="$(ssh orange-pi sha256sum /opt/edge/traefik/dynamic.yml)"
output="$(bash "$script" --host cleanup-probe.dungxbuif.com --target 10.10.0.10:19999 --expose internal)"
after="$(ssh orange-pi sha256sum /opt/edge/traefik/dynamic.yml)"

test "$before" = "$after"
grep -q 'cleanup-probe.dungxbuif.com' <<<"$output"
grep -q '10.10.0.10:19999' <<<"$output"
```

The test asserts the helper defaults to Orange Pi Traefik, contains no Pi5 Caddy writer, displays a proposed route, and leaves the live file unchanged in dry-run mode.

- [ ] **Step 2: Run the test and confirm the old helper fails**

Run:

```bash
rtk bash edge-registrar/tests/test-edge-publish.sh
```

Expected: FAIL because the existing helper targets `/ssd-data/infra/Caddyfile` on Pi5.

- [ ] **Step 3: Implement Traefik YAML updates with Python and PyYAML**

Refactor `edge-publish.sh` to use `python3` on Orange Pi and the VPS for parsed YAML updates. Keep dry-run as default, create a timestamped file backup before `--apply`, reject duplicate router/service names, and validate the resulting YAML before replacement.

The Orange Pi updater must perform these exact parsed-data mutations:

```python
name = host.removesuffix(".dungxbuif.com").replace(".", "-")
routers = data.setdefault("http", {}).setdefault("routers", {})
services = data["http"].setdefault("services", {})
if name in routers or name in services:
    raise SystemExit(f"route already exists: {name}")
routers[name] = {
    "rule": f"Host(`{host}`)",
    "entryPoints": ["websecure"],
    "service": name,
    "tls": {"certResolver": "letsencrypt"},
}
services[name] = {
    "loadBalancer": {"servers": [{"url": f"http://{target}"}]},
}
```

For `--expose public`, the VPS updater must append the exact hostname to the existing `HostSNI(...)` expression only when absent. For `internal`, it must not change the VPS file. Both updaters write to a sibling temporary file, parse that file again, show a unified diff, and use `os.replace()` only in apply mode.

- [ ] **Step 4: Run fixture and live dry-run verification**

Run:

```bash
rtk bash edge-registrar/tests/test-edge-publish.sh
rtk ssh orange-pi 'sha256sum /opt/edge/traefik/dynamic.yml'
rtk bash edge-registrar/scripts/edge-publish.sh --host cleanup-probe.dungxbuif.com --target 10.10.0.10:19999 --expose internal
rtk ssh orange-pi 'sha256sum /opt/edge/traefik/dynamic.yml'
```

Expected: tests pass; dry-run shows the proposed router/service; both live hashes are identical.

- [ ] **Step 5: Commit the helper and tests**

Run:

```bash
rtk git add edge-registrar/scripts/edge-publish.sh edge-registrar/tests/test-edge-publish.sh
rtk git commit -m "infra: publish routes through Orange Pi Traefik"
```

Expected: helper and tests are tracked with no generated fixture output.

---

### Task 4: Reconcile Current Documentation

**Files:**
- Modify: `index.md`
- Modify: `docs/MAIN.md`
- Modify: `docs/LOG.md`
- Modify: `docs/CONTEXT.md`
- Modify: `docs/INDEX.md`
- Modify: `docs/MAC.md`
- Modify: `docs/PI.md`
- Modify: `iac/README.md`
- Modify: `docs/migration_orange_pi_edge.md`
- Test: stale-current-reference scan

**Interfaces:**
- Consumes: canonical stack and verified runtime topology.
- Produces: one consistent operator narrative: VPS Traefik to Rathole to Orange Pi Traefik.

- [ ] **Step 1: Record the pre-existing diffs in overlapping dirty files**

Run:

```bash
rtk git diff -- docs/MAIN.md docs/LOG.md > /tmp/edge-cleanup-preexisting-docs.patch
```

Expected: preserves the pre-existing uncommitted context for review; do not revert it.

- [ ] **Step 2: Update all current architecture and runbook references**

Change current sections to state: VPS `gateway-traefik` forwards through Rathole to Orange Pi `edge_traefik`; Orange Pi AdGuard provides split DNS; Pi5 is manager/datastore only. Remove current instructions for Pi5 Caddy, Orange Pi Caddy, VPS Nginx, and retired `n8n`/`gitlab` routes.

- [ ] **Step 3: Mark the old Orange Pi Caddy migration plan as superseded**

Add a top-level warning to `docs/migration_orange_pi_edge.md` that it is retained as migration history and must not be executed as the current deployment runbook.

- [ ] **Step 4: Verify no active documentation points to retired ingress**

Run:

```bash
rtk rg -n -i 'Pi5 Caddy edge|Orange Pi Caddy|nginx-gateway|Nginx layer|n8n\.dungxbuif\.com|gitlab\.dungxbuif\.com|git\.dungxbuif\.com' index.md docs/MAIN.md docs/CONTEXT.md docs/INDEX.md docs/MAC.md docs/PI.md iac/README.md migration/README.md edge-registrar
```

Expected: no current operational references; historical sections are explicitly labeled superseded or retired.

- [ ] **Step 5: Stage clean files separately and preserve overlapping user changes**

Run:

```bash
rtk git diff --check
rtk git status --short
```

Expected: no whitespace errors. Commit cleanly-owned files; leave `docs/MAIN.md` and `docs/LOG.md` unstaged if their pre-existing unrelated hunks cannot be isolated without absorbing user work.

---

### Task 5: Remove Orange Pi Caddy And Stale Edge Artifacts

**Files:**
- Delete remotely: Swarm service `edge_caddy`
- Delete remotely: `/home/dungxbuif/edge/caddy/`
- Delete remotely: unused Caddy images and redundant backup/test files
- Test: active service count, endpoint smoke tests, exact stale-container inventory

**Interfaces:**
- Consumes: verified rollback archive and active Traefik service.
- Produces: Orange Pi with exactly Traefik, Rathole, and AdGuard edge services.

- [ ] **Step 1: Verify retained routes before deleting Caddy**

Run LAN and VPS `curl --resolve` probes for every hostname in `migration/traefik/dynamic.yml`. Accept service-specific healthy responses such as `200`, `302`, `401`, or intentional `403`; reject connection failures, TLS failures, and Traefik `404` for retained hosts.

- [ ] **Step 2: Remove only the disabled Caddy service**

Run:

```bash
rtk ssh pi 'test "$(docker service inspect edge_caddy --format "{{.Spec.Mode.Replicated.Replicas}}")" = 0 && docker service rm edge_caddy'
```

Expected: `edge_caddy` is removed; the other three services remain `1/1`.

- [ ] **Step 3: Remove exact stale task containers**

List stopped or created containers whose names start with `edge_`, verify every ID, then pass only those explicit IDs to `docker container rm`. Do not use an unrestricted `docker container prune`:

```bash
rtk ssh orange-pi 'docker ps -a --filter status=exited --filter status=created --format "{{.ID}} {{.Names}} {{.Status}}" | grep " edge_"'
```

After reviewing the output, run `docker container rm` with the explicit IDs printed by this command.

- [ ] **Step 4: Remove Caddy files and images after mount verification**

Confirm no running container mount references `/opt/edge/caddy`, then remove `/home/dungxbuif/edge/caddy` through a bounded Docker mount. Remove `caddy:2` and `infra-caddy:latest` only after `docker ps -a` confirms they are unused.

Run:

```bash
rtk ssh orange-pi 'test -z "$(docker ps --format "{{.Mounts}}" | grep /opt/edge/caddy || true)" && docker run --rm -v /home/dungxbuif/edge:/edge busybox:1.36.1 rm -rf /edge/caddy'
rtk ssh orange-pi 'docker image rm caddy:2 infra-caddy:latest'
```

- [ ] **Step 5: Remove redundant Orange Pi backups while preserving active ACME**

Delete `dynamic.yml.bak-*`, `rathole.toml.bak-*`, `traefik-test.yml`, and the obsolete AdGuard migration edit script after verifying they exist in the rollback archive. Do not rename or delete `test-letsencrypt/acme.json`.

Use only these exact targets:

```bash
rtk ssh orange-pi 'rm -f /home/dungxbuif/edge/traefik/dynamic.yml.bak-20260908-family /home/dungxbuif/edge/traefik/dynamic.yml.bak-mezonhook-20260907 /home/dungxbuif/edge/traefik/traefik-test.yml /home/dungxbuif/edge/rathole/rathole.toml.bak-20260824-ssl /home/dungxbuif/edge/rathole/rathole.toml.bak-20260824-overlay /home/dungxbuif/edge/rathole/rathole.toml.bak-goclaw-20260902151615 /home/dungxbuif/edge/adguard/edit-for-orange-pi.sh'
```

- [ ] **Step 6: Verify Orange Pi cleanup**

Run:

```bash
rtk ssh orange-pi 'docker ps --format "{{.Names}} {{.Status}}" | grep ^edge_; docker images --format "{{.Repository}}:{{.Tag}}" | grep -E "caddy|traefik|rathole|adguard"; find -L /opt/edge -maxdepth 3 -type f -print | sort'
```

Expected: only retained services and images remain; no Caddy tree or redundant backups remain; active Traefik ACME JSON remains.

---

### Task 6: Remove Pi5 And VPS Legacy Edge Assets

**Files:**
- Delete remotely on Pi5: `/ssd-data/infra/caddy/`, `/ssd-data/infra/rathole/`, `/ssd-data/infra/adguard/`, `/ssd-data/infra/_pre-orange-pi/`, `/ssd-data/infra/docker-compose.yml.bak-20260824-remove-pi5-edge`
- Delete remotely on VPS: `/root/gateway/nginx.conf`, `/root/gateway/nginx.conf.bak-*`
- Test: mount/image ownership checks and active-container checks

**Interfaces:**
- Consumes: verified rollback archive and current container mount inventory.
- Produces: Pi5 and VPS without inactive ingress implementations.

- [ ] **Step 1: Prove Pi5 legacy paths and images are unused**

Run:

```bash
rtk ssh pi 'docker ps -a --format "{{.Names}} {{.Image}} {{.Mounts}}" | grep -E "/ssd-data/infra/(caddy|rathole|adguard|_pre-orange-pi)" || true; grep -nE "^[[:space:]]{2}(caddy|rathole|adguardhome):" /ssd-data/infra/docker-compose.yml || true'
```

Expected: no active or stopped container references these paths and the current compose defines none of the retired services.

- [ ] **Step 2: Remove exact Pi5 legacy paths and unused images**

Delete only the five paths listed in this task. Remove `infra-caddy:latest`, `rathole:local`, and `adguard/adguardhome:latest` only after Docker confirms no container references each image.

Run after Step 1 passes:

```bash
rtk ssh pi 'rm -rf /ssd-data/infra/caddy /ssd-data/infra/rathole /ssd-data/infra/adguard /ssd-data/infra/_pre-orange-pi && rm -f /ssd-data/infra/docker-compose.yml.bak-20260824-remove-pi5-edge'
rtk ssh pi 'docker image rm infra-caddy:latest rathole:local adguard/adguardhome:latest'
```

- [ ] **Step 3: Prove VPS Nginx is inactive**

Run:

```bash
rtk ssh gateway 'docker ps -a --format "{{.Names}} {{.Image}}" | grep -i nginx || true; grep -nE "nginx.conf|nginx-gateway" /root/gateway/docker-compose.yml || true; docker ps --filter name=gateway-traefik --format "{{.Names}} {{.Status}}"'
```

Expected: no Nginx container or compose reference exists and `gateway-traefik` is running.

- [ ] **Step 4: Remove exact VPS Nginx files**

Delete `/root/gateway/nginx.conf` and files matching `/root/gateway/nginx.conf.bak-*`; leave `dynamic.yml`, `traefik.yml`, certificates, Rathole, Headscale, and application files untouched.

Run:

```bash
rtk ssh gateway 'rm -f /root/gateway/nginx.conf /root/gateway/nginx.conf.bak-20260708153546 /root/gateway/nginx.conf.bak-20260901134103'
```

- [ ] **Step 5: Verify cleanup targets are absent**

Run exact `test ! -e` checks for every removed path and list retained gateway/edge services.

---

### Task 7: End-To-End Verification And Handoff

**Files:**
- Test: runtime, DNS, LAN ingress, VPS ingress, retired routes, PostgreSQL baseline, Git diff

**Interfaces:**
- Consumes: all prior task outputs.
- Produces: evidence that cleanup preserved the intended production path.

- [ ] **Step 1: Verify cluster and retained services**

Run:

```bash
rtk ssh pi 'docker node inspect orangepizero3 --format "{{.Status.State}} {{.Status.Addr}}"; docker service ls --format "{{.Name}} {{.Replicas}}" | grep ^edge_'
```

Expected: node is `ready`; exactly `edge_traefik`, `edge_rathole`, and `edge_adguardhome` are `1/1`.

- [ ] **Step 2: Verify split DNS and retained routes over LAN and VPS**

Resolve each retained hostname through `10.10.0.2`, then probe HTTPS once with `--resolve <host>:443:10.10.0.2` and once with `--resolve <host>:443:103.82.21.202`. Record every status and reject transport/TLS failures.

- [ ] **Step 3: Verify retired routes are absent**

Run local Orange Pi probes for `n8n`, `gitlab`, `git`, and `grafana` and require Traefik `404`. Confirm none appears in `migration/traefik/dynamic.yml` or `/opt/edge/traefik/dynamic.yml`.

- [ ] **Step 4: Verify PostgreSQL is unchanged**

Repeat the exact Task 1 PostgreSQL status command and compare image, status, ports, and container identity. Do not execute SQL, restart the container, or alter networking.

- [ ] **Step 5: Verify repository and secret hygiene**

Run:

```bash
rtk git diff --check
rtk rg -n 'CF_DNS_API_TOKEN: [^$]|CF_API_TOKEN: [^$]|token[[:space:]]*=' migration edge-registrar docs --glob '!docs/archived/**'
rtk git status --short --branch
```

Expected: no whitespace errors or committed plaintext secrets; only known pre-existing unrelated changes remain unstaged.

- [ ] **Step 6: Commit remaining cleanly-owned documentation changes**

Stage only files and hunks owned by this cleanup and commit with:

```bash
rtk git commit -m "docs: reconcile Traefik edge topology"
```

Expected: commit excludes unrelated GoClaw SSRF and access-platform planning changes unless the user explicitly includes them.
