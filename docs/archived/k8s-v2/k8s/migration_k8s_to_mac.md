---
type: Plan
title: "Migration Plan: K8s cluster → Mac mini (consolidation)"
status: draft
created: 2026-08-17
supersedes: ./migration_plan.md (that doc is the reverse direction: Pi5 → K8s)
---

# 🧭 Migration Plan: K8s → Mac mini

Migrate all **user-facing services** currently running in the 3-node Proxmox K8s cluster
(`k8s-cp-1/2/3`, VIP `10.10.0.30`) onto **this machine**, the Mac mini
(`10.10.0.10`, macOS arm64, 12 cores / 48 GB RAM / Docker + Compose).

> [!NOTE]
> The **database tier (PostgreSQL + VictoriaMetrics) stays on the Pi `10.10.0.5`** for this
> phase — it was never in K8s. Apps on the Mac can reach the Pi over LAN, so DB migration is
> out of scope here. Only K8s-hosted services move.

---

## 1. Current K8s state (inventory)

3 control-plane nodes, Cilium CNI, Traefik ingress (LB `10.10.0.30`), Longhorn storage,
ArgoCD GitOps (`homelab-ops` repo). Apple domains terminate at **VPS Traefik → Rathole tunnel → on-prem (K8s VIP)**.

### Classification

| Namespace | Workload | Image | Type | Disposition |
|---|---|---|---|---|
| homepage-prod | homepage | `registry.dungxbuif.com/homepage:prod-2026.08.06.2` | stateless web | **MIGRATE** |
| macocr | macocr-proxy (+ HPA) | `registry.dungxbuif.com/macocr-proxy:v1.0.2` | stateless api | **MIGRATE** |
| omniscan | omniscan-bot | `registry.dungxbuif.com/omniscan:v1.0.0` | bot | **MIGRATE** |
| redis | redis | `redis:7.2-alpine` (auth) | stateful (cache) | **MIGRATE** |
| localstack | localstack | `localstack/localstack:3.8.1` | stateful (PVC 8Gi) | **MIGRATE + data** |
| monitoring | grafana | `grafana/grafana-oss:latest` | stateful (PVC 5Gi) | **MIGRATE + data** |
| monitoring | kube-state-metrics | ksm | k8s-only metric scraper | **DROP** (replace w/ node-exporter/cadvisor) |
| gitlab-runner | gitlab-runner | `gitlab-runner:alpine-v19.2.0` | CI runner | **MIGRATE** (optional) |
| argocd | argocd-* (7 pods) | argocd v3.5 | GitOps controller | **DECISION** → see §3 |
| traefik | traefik (DS) | traefik v3.7 | ingress | **REPLACE** by local reverse proxy |
| kube-system | cilium/kube-proxy/coredns/kube-vip/hubble/metrics-server/sealed-secrets | — | cluster infra | **DROP** (not needed on single host) |
| longhorn-system | longhorn + csi | — | storage | **DROP** (use Docker volumes/bind) |
| homepage-dev | *(empty)* | — | — | already gone |

**Stateful data to move**: `localstack/localstack-data` (8 Gi), `monitoring/grafana-pvc` (5 Gi).
Redis ≈ cache (verify no durable requirement before discarding).

---

## 2. Target machine — readiness

- **OS**: macOS Darwin arm64 (Mac mini), 12 cores, 48 GB RAM.
- **Docker**: 29.5.2 + Compose v5.1.3 ✅
- **Disk**: `/` 460 Gi, ~48 Gi free (APFS). Headroom OK for ~16 Gi of PVCs + images, but
  put hot data under a dedicated path (e.g. `~/dev-env` already used for dev DBs) and **watch it**.
- **Network**: `10.10.0.10` (eth) / `10.10.0.11` (wifi) / WG `10.0.0.3`. Same L2 as Pi & K8s ✅
- **Already running dev containers**: `postgres` (:5432), `redis` (:6379), `mongo` (:27017)
  under `~/dev-env/database` — **dev creds**, separate from prod. ⚠️ Port conflict with the
  prod Redis we need; resolve in §3.

---

## 3. Open decisions (confirm before executing)

1. **Reverse proxy choice**: `Caddy` (recommended, simplest) vs keep `Traefik v3`
   (familiar parity with K8s). Both route by `Host` on `10.10.0.10:80`.
2. **Rathole repoint**: confirm VPS Rathole *server* config forwards to on-prem client which
   targets `10.10.0.30` today → change to `10.10.0.10`. (Assumes Rathole client runs on-prem.)
3. **ArgoCD**: drop GitOps for a single host → manage via `git + docker compose` (pull/up on
   push via GitLab CI SSH), **or** keep a tiny ArgoCD? Recommend: **drop**, use compose + CI.
4. **Redis consolidation**: stand up **one prod Redis (auth, 7.2-alpine)** and stop the
   standalone dev redis, OR run prod redis on a different port. Recommend: prod redis on an
   internal compose network (no host port) + keep dev redis as-is.
5. **GitLab runner**: re-register on the Mac (new token) or retire? (It's needed if you want
   CI builds on-prem.)
6. **Decommission K8s cluster?** Full teardown of the 3 Proxmox nodes, or keep idling as DR?
   Plan assumes **full decommission** after cutover.

---

## 4. Proposed target layout on the Mac

```
~/workspace/homelab/compose/
  docker-compose.yml            # production stack (infra + apps)
  .env                          # sourced from local_vars.json / credentials/
  reverse-proxy/
    Caddyfile                   # routes *.dungxbuif.com -> container services
  data/                         # bind-mounted persistent data (or -> ~/dev-env)
    redis/
    localstack/
    grafana/
  README.md
```

Keep IaC for K8s in `iac/k8s/**` and `kubernetes/**` untouched until cutover (DR reference).

---

## 5. Phased execution

### Phase 0 — Prep (no downtime)
- [ ] Confirm §3 decisions.
- [ ] Create `compose/` dir + `.env` (reference `local_vars.json` keys, not raw secrets).
- [ ] Add GitLab registry login on the Mac:
      `echo "$REGISTRY_PASSWORD" | docker login registry.dungxbuif.com -u dungxbuif --password-stdin`
      (creds: `LEGACY_SYSTEM_SECRETS.REGISTRY_*`).
- [ ] Pull all prod images to warm local cache:
      `homepage:prod-2026.08.06.2`, `macocr-proxy:v1.0.2`, `omniscan:v1.0.0`,
      `redis:7.2-alpine`, `localstack:3.8.1`, `grafana-oss:latest`.

### Phase 1 — Shared data service: Redis (prod)
- [ ] Stand up prod Redis `redis:7.2-alpine` with `requirepass` = `MACOCR_SECRETS.MACOCR_REDIS_PASSWORD`,
      internal compose network `homelab`, no host port (or :6390 to avoid dev :6379 clash).
- [ ] Healthcheck `redis-cli -a ... ping`.
- [ ] Note new internal DNS: `redis://:<pwd>@redis:6379/0` (compose service name `redis`).

### Phase 2 — Reverse proxy + Rathole cutover (traffic pivot)
- [ ] Run Caddy (or Traefik) bound to `10.10.0.10:80`, routing:
      - `dungxbuif.com`, `www.`, `home.` → `homepage:80`
      - `ocr.` → `macocr-proxy:8080`
      - `localstack.` → `localstack:4566`
      - `grafana.` → `grafana:3000`
      - `argocd.` → (drop or keep per §3.2)
- [ ] Update on-prem Rathole client target: `10.10.0.30` → `10.10.0.10`.
- [ ] Verify each domain from LAN + via VPS.

### Phase 3 — Stateless apps (no data)
- [ ] **homepage**: service `homepage`, image `registry.dungxbuif.com/homepage:prod-2026.08.06.2`,
      port 80, no env secrets (only `regcred` needed → compose uses `docker login` creds).
- [ ] **macocr-proxy**: image `registry.dungxbuif.com/macocr-proxy:v1.0.2`, port 8080,
      env from `MACOCR_SECRETS` (ADMIN, NATIVE_AUTH_SECRET, NOTIFICATION_ENCRYPTION_KEY,
      DATABASE_URL=Pi postgres `10.10.0.5:5432/macocr`, REDIS_URL→new compose redis).
      Drop HPA (single host). Replicas: 1 (scale manually if needed).
- [ ] **omniscan-bot**: image `registry.dungxbuif.com/omniscan:v1.0.0`, env from `OMNISCAN_SECRETS`
      (DATABASE_URL=Pi `10.10.0.5:5432/omniscan`, REDIS_URL→compose redis, OCR_PROXY_URL,
      LLM_* , MEZON_*). `restart: unless-stopped`.
- [ ] Smoke test: `curl ocr.dungxbuif.com/health`, bot responds in Mezon.

### Phase 4 — Stateful apps (with data migration)
- [ ] **localstack** (PVC 8 Gi):
      - Export: `kubectl exec -n localstack localstack-... -- tar czf - /tmp/localstack/data | > data/localstack/ls.tgz`
        (confirm exact data path inside pod first).
      - Restore into bind `data/localstack/`, run `localstack/localstack:3.8.1`
        with `SERVICES=...` matching current, ports `4566` (+4510-4515).
      - Route `localstack.dungxbuif.com` → `localstack:4566`.
- [ ] **grafana** (PVC 5 Gi, sqlite + plugins/dashboards):
      - Export: `kubectl cp monitoring/grafana-...:/var/lib/grafana ./data/grafana` (or tarball).
      - Run `grafana/grafana-oss:latest`, bind `data/grafana:/var/lib/grafana`,
        provision datasource `VictoriaMetrics @ http://10.10.0.5:8428` (unchanged).
      - Route `grafana.dungxbuif.com` → `grafana:3000`.
      - Verify dashboards present post-import.

### Phase 5 — CI runner (optional)
- [ ] Re-register `gitlab-runner` on Mac (new registration token from GitLab) or migrate
      existing config from `gitlab-runner` cm/secret. Run as compose service. Pin
      `gitlab-runner:alpine-v19.2.0`.

### Phase 6 — Decommission K8s
- [ ] Final verification (§7) → keep cluster 24–48h as DR.
- [ ] Drain & delete workloads, then tear down Longhorn → nodes via `iac/terraform`.
- [ ] Update `local_vars.json` `K8S_VIP`/`K8S_CP*_IP` → mark Deprecated. Repoint any remaining
      references (`*.svc.cluster.local` → compose service names) in app configs.
- [ ] Remove `registry-secret`/sealed-secrets now that images pull via `docker login`.

---

## 6. K8s → Compose mapping (quick reference)

| K8s object | Compose equivalent |
|---|---|
| Deployment + Service | `services.<name>` (+ `ports`/`expose`) |
| Ingress `host → svc:port` | Caddyfile `host { reverse_proxy <svc>:<port> }` |
| Secret `macocr-secrets` | `.env` + `environment:` (from `local_vars.json`) |
| ConfigMap `redis-config` | inline `command:`/`volumes` redis.conf |
| PVC (Longhorn) | bind mount `./data/<svc>` or named volume |
| `imagePullSecrets` / `regcred` | host `docker login` (compose reuses host creds) |
| HPA (`macocr-hpa`) | n/a — fixed replicas |
| `*.svc.cluster.local` DNS | compose service-name DNS (network `homelab`) |

---

## 7. Verification checklist

- [ ] `docker compose ps` all services `healthy`.
- [ ] `curl -H 'Host: dungxbuif.com' http://10.10.0.10` → homepage.
- [ ] `curl -H 'Host: ocr.dungxbuif.com' .../health` → 200.
- [ ] Omniscan bot answers a test message.
- [ ] `localstack.dungxbuif.com` → S3 list works (data present).
- [ ] `grafana.dungxbuif.com` → log in, dashboards + VictoriaMetrics datasource OK.
- [ ] Apps still reach Pi DB: `nc -vz 10.10.0.5 5432` from inside macocr/omniscan containers.
- [ ] Redis auth works: `redis-cli -a $PWD -h redis ping` → PONG.
- [ ] Resource headroom: `docker stats` < ~6 GB RAM / low CPU; disk `<data>`.
- [ ] After 48h DR window: `kubectl get nodes` returns nothing in `~/.kube/config` removed.

---

## 8. Rollback

- Keep K8s cluster up during DR window; Rathole target is a single line — flip
  `10.10.0.10` back to `10.10.0.30` to restore traffic to K8s instantly.
- Compose services are additive; `docker compose down` removes them without touching K8s.
- Data exported to `compose/data/**` is a copy — originals stay on Longhorn until teardown.

---

## 9. Risks

- **Disk on `/`**: only ~48 Gi free; monitor `data/` growth (localstack/grafana) — move to a
  larger external volume if it grows.
- **macOS Docker I/O**: bind mounts on macOS go through VirtioFS; fine for these sizes but
  avoid high-IOPS workloads.
- **Sleep/WiFi**: Mac mini on WiFi (`10.10.0.11`) is unreliable for a server — **force Ethernet
  `10.10.0.10` and prevent sleep** (`caffeinate` / Energy Saver).
- **Secret sprawl**: prefer one `.env` from `local_vars.json`; avoid pasting raw secrets into compose YAML.
- **Image registry dependency**: `registry.dungxbuif.com` (GitLab Container Registry on VPS)
  must stay up; mirror critical images locally if VPS is flaky.
