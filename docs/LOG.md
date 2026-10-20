---
type: Reference
title: 'Directory Update Log'
description: 'Changelog and historical context updates for the Homelab documentation files'
timestamp: 2026-07-03T15:14:00Z
---

# Directory Update Log

> **Versioning scheme** (architecture evolution, newest first):
> - **v3.4** — Pi5 active edge, VM100 production worker, active backup runner, and Semaphore provisioning control plane
> - **v3.3** — VM100 production compute + Pi5 edge recovery
> - **v3.2** — VM100 production compute + Orange Pi Traefik edge
> - **v3.1** — Orange Pi Zero 3 edge migration (Pi5 → datastore only)
> - **v3.0** — Mac mini consolidation (K8s retired, Proxmox → AWS lab)
> - **v2** — Proxmox 3-node K8s cluster (archived → [`archived/k8s-v2/`](./archived/k8s-v2/))
> - **v1** — legacy pre-repo history (referenced in old dated entries only)
>
> Dated entries below are grouped under their architecture version heading.
> Every significant change appends to this log; the current version marker also
> lives in [`index.md`](../index.md) and [`MAIN.md`](./MAIN.md).

## 2026-10-19 - Audit and network hardening (in progress)

- **Audit:** full security, backup and automation audit plus a network and
  workload review; see
  [network-workload-automation-audit-2026-10-19.md](./research/network-workload-automation-audit-2026-10-19.md).
- **Live changes:** VPS legacy tunnel ports blocked, SSH key-only, coturn
  restricted, `pg-net` and `s3-net` overlays created, whiteboard moved onto
  `pg-net`, VM100 cache pruned, RelayHub and Stirling PDF restored. Details,
  verification and rollback in
  [network-hardening-2026-10-19.md](./deployments/network-hardening-2026-10-19.md).
- **Exposure (2026-10-20):** `pgadmin` and `couchdb` host are LAN-only on Pi5; `sync-db` is the only public CouchDB name and is path-restricted to the vault DB.
- **Open:** public GitHub repo with exposed credentials (rotation deferred),
  remaining consumers to move off `homelab-net`, backup gaps (configs, VM100
  vzdump, dead-man's switch, Drive restore acceptance).

## 2026-10-15 - Automation and runtime reconciliation

- **Backup health gate:** Semaphore task 57 passed the combined read-only
  health check. It confirmed free space, a free backup lock, and fresh
  PostgreSQL/CouchDB, RustFS, and GitLab success markers. Remote Drive restore
  remains open and is tracked separately.
- **Homepage release notification:** Semaphore task 56 passed the dedicated
  Mezon notification boundary using the secret Variable Group; the generic
  application deploy template remains unenrolled/design-only.
- **Policy correction:** Pi5 `node-exporter` was observed running despite the
  retired topology documentation. Its service removal and post-check are
  tracked in [the retirement record](./deployments/node-exporter-retirement-2026-10-15.md).

## 2026-10-13 — Runtime reconciliation

- **Runtime inventory refreshed:** Pi5 (`rpivn`, Docker `28.4.0`) is the active
  standalone Traefik/Rathole/AdGuard edge and Swarm manager. VM100
  (`vm100-prod`, Docker `29.1.3`) is the production worker and Compose host.
  Orange Pi is still `Down`; old Swarm edge services remain `0/0`.
- **Recent deployment versions reconciled:** current image tags and observed
  image IDs for RelayHub `prod-eee9e7c`, CouchLoom `8f7a8e0`, MyPocket release
  images, OCR `scan-api-20261008`, Homepage `vm100-20261007-stirling`, K8s
  Syntax `af8481e`, GitLab CE `18.11.11-ce.0`, Stirling `3.1.0`, NetBird,
  KubeKosh, OpenClaw, n8n, and the GitLab tunnel clients are recorded in the
  [runtime inventory](./deployments/runtime-inventory-2026-10-13.md).
- **Backup state reconciled:** VM100 timers remain enabled. The latest Pi5
  class markers are successful for databases (`databases-20261012-180003`),
  RustFS (`rustfs-20261012-213004`), and GitLab (`gitlab-20261012-193002`) with
  fresh remote snapshot IDs. The health oneshot itself last exited 1 because it
  ran before two markers existed and logged a start-time parsing warning; this
  reporting defect remains explicitly open and is not hidden by the later class
  success markers.
- **GitLab notification mismatch fixed:** GitLab's VM100 runner had a stale
  121-byte Mezon webhook secret while Pi5 used the current 205-byte secret.
  The secret was synchronized with mode `0640` and matching SHA-256; one
  warning-level delivery probe returned successfully. The next scheduled
  GitLab run is the normal success-notification confirmation.
- **Semaphore metadata reconciled:** restored task history from the preserved
  SQLite snapshot, kept one project/template/user/access key, and normalized
  the UI field labels and task messages. The current `db-provision` workflow is
  a private database/user provisioning control plane, not a second backup
  scheduler.
- Updated the catalog, Pi5/VM100 host references, backup runbook, and
  provisioning runbook so “pilot”, “pending”, and Orange Pi edge statements
  remain only where they describe historical state.

## 2026-10-07

- **Backup OAuth project corrected (2026-10-08):** created a new desktop OAuth
  client in the dedicated Google Cloud project `homelab-backup-488616`, enabled
  the Drive API there, and installed the resulting private rclone config on
  Pi5 and VM100. The existing `Homelab Backup/homelab-backups/` root and
  `databases`, `gitlab`, and `rustfs` repositories were preserved; the older
  client config is archived on each host for rollback. `rclone about` and
  repository directory checks pass. Database run
  `databases-20261008-014054` uploaded with the new client, passed the Restic
  metadata/tree check plus a `1/100` read-data subset using temporary
  maintenance pacing, sent a successful Mezon post-check, and wrote a fresh
  success marker. Nine duplicate pack files remain as a non-critical warning;
  no prune or retention cleanup was run.

- **Database backup failure remediation started (2026-10-08):** the two
  database alerts were traced to a stale Restic repository lock left by a dead
  process; the newer retry is still online while its large CouchDB export and
  Drive upload complete. The fix will recover stale locks only after checking
  that no local Restic process is active, remove SIGPIPE-prone path-capture
  pipelines, and require the existing remote post-check before marking the
  class successful. Retention remains blocked until all class markers are
  fresh. The Restic operation timeout was also raised from two to four hours
  because the paced, project-owned Drive client can take longer for the large
  CouchDB export; the systemd service timeout remains the outer limit. The
  Pi5 deployment also removes SIGPIPE-prone path capture and includes the
  failing runner stage in Mezon diagnostics; a live database retry is still
  uploading and has not yet written a success marker.

- **Stirling-PDF deployed on VM100:** Added the portless Swarm service
  `stirling-pdf` on `homelab-net` using the pinned official `3.1.0` image,
  persistent config/OCR/pipeline mounts, login, 2 CPU/2 GiB limits, and
  bounded Docker JSON logs. Orange Pi Traefik now routes the hostname to
  `tasks.stirling-pdf:8080`; Homepage was rebuilt with a Stirling PDF link.
  LAN/edge HTTPS and overlay health checks pass. VPS HostSNI admission remains
  pending because the gateway SSH agent was unavailable; direct VPS probe is
  currently 404 while the edge probe is 200.
- **VM100 resource audit:** 9.0 GiB RAM available after deployment and 56 GiB
  disk free. Docker has a 16 GiB GitLab JSON log without rotation, 3.8 GiB of
  systemd journal, 61 stopped containers, and three dangling images. Docker
  system-df also reports a missing overlay snapshot, so cleanup is deferred to
  a maintenance window rather than running an unsafe blanket prune.
- **Backup overnight failure repaired/diagnosed:** Timers did run, but the
  first window failed on runtime drift, an unreadable VM100 lock/secret setup,
  and a RustFS stdout path-capture bug. The wrapper, lock path, secret modes,
  health class list, and path capture were corrected; a manual health run
  reached Mezon notification without a delivery error. Local DB, RustFS, and
  GitLab exports are complete, while all Drive Restic uploads remain blocked
  by Google Drive `RATE_LIMIT_EXCEEDED`; no retention or local cleanup ran.
  Follow-up confirmed Drive has about 1.27 TiB free; the remaining blocker is
  API project quota because the rclone config uses the shared/default OAuth
  client and has no project-owned `client_id`/`client_secret`. The runner now
  preserves quota diagnostics, bounds preflight retries, and reports failed
  classes immediately. A new remote snapshot is intentionally not claimed
  until the project-owned client is installed and all three classes pass.

## 2026-10-06

- **Backup automation enabled:** VM100 now has active systemd timers for
  PostgreSQL/CouchDB, GitLab, RustFS, retention, and read-only health checks.
  Pi5 remains the database/object-storage executor. The runner uses the
  pinned Google Drive root and the already populated
  `Homelab Backup/homelab-backups/` Restic repositories; local staging keeps
  the two newest completed runs per class and preserves incomplete runs. The
  first scheduled end-to-end window is still pending.
- **Backup preflight note:** all three populated legacy Restic repositories
  opened successfully in read-only checks. A controlled retention run was
  stopped after repeated Google Drive rate-limit responses; no remote prune or
  local staging deletion occurred, and the lock/process cleanup was verified.
- **Overnight verification prepared:** VM100 backup and health services now
  emit class-specific journald identifiers, and the scheduler/health systemd
  units pass `systemd-analyze verify`. The 2026-10-07 window is intentionally
  left to the timers; morning review will inspect journal results, marker ages,
  Drive rate-limit errors, and the retention cleanup gate before any manual
  retry.
- **Backup scheduler re-enable started:** the replacement schedule will run on
  VM100, invoke database/RustFS executors on Pi5 over a restricted SSH key,
  keep GitLab native backup local to VM100, and retain the native post-check plus
  Mezon notification contract. The retired `simple-backup.sh` cron remains off.
- **Private provisioning control plane:** Deployed Semaphore UI plus the internal
  `homelab-provisioner` service on Pi5. Semaphore remains LAN/NetBird-only and
  has no Docker socket; the provisioner is the only Docker API holder, has no
  published port, and accepts only the Swarm token secret. The `db-provision`
  workflow now creates PostgreSQL or CouchDB resources, smoke-tests the owner,
  and enrolls successful resources in the backup catalog without returning
  generated credentials.
- **Verification:** PostgreSQL and CouchDB disposable staging canaries passed
  through the full Semaphore -> Ansible -> provisioner path. Both were removed
  completely, including users, Swarm secrets, and catalog rows. The first
  scheduled end-to-end backup window remains the final live verification.

## v3.2 — 2026-10-05 · Backup and restore rehearsal

- Ran the current PostgreSQL/CouchDB inventory online on Pi5 and produced a
  complete, checksummed local run with paginated CouchDB exports. Restored one
  PostgreSQL database and one CouchDB database into disposable targets, then
  removed only those test targets.
- Ran the RustFS S3/API export for all 8 approved buckets and restored an
  isolated bucket. Fixed the restore verifier so backup control metadata is not
  copied into production object namespaces.
- Ran the VM100 GitLab native backup online, including config/secrets and local
  Registry artifacts. Restored its SQL into a PostgreSQL 17 disposable target
  after loading globals; the run records PostgreSQL 16.14 server and 17.10
  dump-client versions. See [rehearsal evidence](./deployments/backup-restore-rehearsal-2026-10-05.md).
- Restic/rclone disposable Drive tooling passed init, backup, check, restore,
  comparison, and cleanup. A first real upload exposed the need for a writable
  per-process OAuth config copy; that fix is covered by the restic contract
  test. Production Drive snapshots, Mezon post-checks, retention, and the
  VM100 scheduler remain pending.

- **CouchLoom deployed to VM100 (2026-10-05):** built and started the pinned
  image `couchloom:vm100-20261005-direct-couchdb` under
  `/opt/apps/couchloom/src` with the existing runtime config. The service is
  private and portless, attached to `homelab-net` for direct access to the
  existing CouchDB source of truth, with PostgreSQL/pgvector and Ollama on its
  private bridge. Container health is `healthy`; metadata indexing loaded the
  `personal` vault with `1,223` notes. Authenticated MCP `initialize`,
  `tools/list`, and `list_vaults` probes passed. RAG backfill was intentionally
  left running in the background (`509` documents / `1,411` chunks at the
  verification point). The optional local LiveSync CLI runner is not deployed
  on VM100. Ollama initially reached roughly `570%` CPU during backfill, so its
  Compose service is now capped at `2.0` vCPU; the embedding endpoint remains
  healthy with lower throughput. GPU passthrough is not currently available.
  OpenClaw registration and production write-back UAT remain pending.

- **CouchLoom LiveSync verification (2026-10-05):** confirmed the production
  design uses the vendored LiveSync common library directly against the
  `obsidian_vault` CouchDB database; the optional CLI runner is not deployed
  on VM100. Local verification passed the production build, `225` repository
  tests with `2` pgvector skips, the disposable CouchDB obfuscation suite, and
  a `linux/amd64` Docker image build. The current VM100 host key was observed
  as `SHA256:Dc7bRD6/p0X/WPlfJCZIb/NHifojNv2GAKam1b0v7fg` through the Pi5
  manager. VM100 deployment was subsequently completed with the homelab SSH
  key `id_homelab_k8s`; no secrets were added to the repository.

---

## v3.2 — 2026-10-04 · Backup runbook and post-check reporting

- Added the [backup and restore runbook](./runbooks/backup-restore.md) and
  agent-readable [backup automation README](../backup/README.md). The contract
  prioritizes native application CLI/API mechanisms, excludes Redis/NATS, keeps
  scheduled backups online, and separates PostgreSQL/CouchDB, GitLab, and
  RustFS recovery workflows.
- Added `backup/scripts/post-check-report.sh` and
  `backup/scripts/notify-mezon.sh`. Each backup class must verify its manifest,
  completion marker, checksums, coverage, and remote snapshot before sending a
  status message to the configured Mezon webhook. The webhook URL is runtime
  secret material and is not stored in the repository.
- Scheduled backup deployment remains pending; no production service,
  database, Google Drive object, or webhook was changed by this documentation
  update.

---

## v3.2 — 2026-09-13 · VPS access and relay cleanup

- **MyPocket AI provider config sync (2026-09-24):** aligned production
  `AI_BASE_URL`, `AI_API_KEY`, `AI_MODEL`, `OCR_API_URL`, and `OCR_API_KEY`
  with the local development config; DeepSeek-V4-Flash is configured. Values
  belong only in gitignored `local_vars.json` → `MYPOCKET_SECRETS` and the
  ignored MyPocket `backend/.env.local`, never in docs or commits. API task
  healthy; web and API health returned 200. Provider inference remains pending
  owner UAT. See [deployment note](./deployments/mypocket-ai-config-2026-09-24.md).

- **NetBird external relay added (2026-09-17):** deployed VPS
  `netbird-relay` with `netbirdio/relay:latest`, TCP `443` behind the existing
  VPS Traefik HostSNI router for `netbird-relay.dungxbuif.com`, and public
  UDP `3478` for STUN. VM100 NetBird server now uses external `stuns/relays`
  and logs `Relay: false`; Pi5 AdGuard has a specific
  `netbird-relay.dungxbuif.com -> 103.82.21.202` rewrite before the wildcard
  LAN rewrite. Verified relay TLS returns expected `404`, NetBird UI returns
  `200`, and relay logs show a peer connection through the VPS Traefik network.

- **Documentation and stack audit (2026-09-16):** added the current
  [stack catalog](./STACK.md) and root agent navigation surface; reconciled
  Proxmox/VM100 roles, MyPocket dev versus production, GitLab isolated
  tunnels, and proposed versus deployed networking. Preserved superseded
  index/MAIN/Proxmox documents in the archive and repaired historical links.
  VM100 inventory and selected public HTTPS probes were checked; Pi5/VPS
  SSH authentication and Orange Pi SSH timeout limit host coverage. No
  production configuration or data changed. See
  [audit evidence and remaining work](./research/docs-stack-audit-2026-09-16.md).
- **GitLab Container Registry isolated trial (2026-09-16 local):** enabled
  the bundled Registry with VM100 filesystem storage and legacy metadata,
  kept Pi5 `docker-registry`/`registry.dungxbuif.com` production unchanged.
  A separate Noise Rathole client/server uses VPS control `7003` and
  Docker-private backend `8086`; VPS Traefik labels serve only
  `registry-gitlab.dungxbuif.com` with valid TLS. GitLab was replaced only
  after the old task stopped, using a versioned Swarm config. Private
  `root/registry-trial` accepted ARM64 push/pull and AMD64 push; a one-time
  GitLab backup archive includes Registry manifest/layers. Existing web,
  SSH, n8n, and Pi5 registry checks passed. Lab split DNS still points the
  trial domain to Orange Pi without a live route, so native Swarm pull and
  production cutover remain pending. See
  [trial report](./deployments/gitlab-registry-trial-2026-09-16.md).
- **GitLab temporary public HTTPS and registration guard (2026-09-16
  local):** added an isolated VPS Rathole HTTP server (`7002` outbound
  client control, backend `8085` only on VPS `gateway-network`) and a
  portless VM100 Swarm client to `tasks.gitlab_gitlab:80`. VPS Traefik
  Docker labels terminate TLS for only `gitlab.dungxbuif.com` with a
  valid Let's Encrypt certificate. A guarded in-place edit removed only
  GitLab from VPS TCP passthrough; backup is retained, and production
  Rathole/Orange Pi tasks were not restarted. Public sign-in and login
  CSS return 200; six pre-existing routes and Git SSH fingerprint passed
  after cutover. Disabled GitLab self-registration after operator approval;
  public sign-up redirects to sign-in. Orange Pi direct GitLab still 404,
  and clone/push/pull plus off-host backup/restore remain unverified. See
  [runbook](./services/gitlab.md).
- **GitLab public SSH (2026-09-15):** added an isolated VPS Rathole server
  on `7001/tcp` (VM100 control) and `2222/tcp` (Git SSH), plus a portless
  VM100 Swarm client to `tasks.gitlab_gitlab:22`. A dedicated token and
  Noise server key were generated outside the repo; public SSH banner and
  ED25519 host fingerprint matched the GitLab container. The existing VPS
  `7000`/HTTPS tunnel and Orange Pi tasks were not restarted. HTTPS still
  returns 404 because the Orange Pi router cannot be applied while admin
  SSH resets before key exchange. See [runbook](./services/gitlab.md).
- **GitLab CE internal deployment (2026-09-15):** deployed pinned
  `gitlab/gitlab-ce:18.11.11-ce.0` as VM100 Swarm `gitlab_gitlab` with
  no host ports, 10 GiB/4 CPU cap, and 256 MiB `/dev/shm` tmpfs. Created
  own Pi5 `gitlabhq_production` database/role, required extensions, and
  Swarm secrets; shared Redis uses DB2 under 1 GiB `noeviction`. Internal
  login/SSH and second `gitlab:check` passed after restarting Gitaly to
  restore a socket unlinked during an overlapping task rollout. HTTPS
  routing still awaits Orange Pi admin access; no off-host
  backup or SMTP is yet verified. See [runbook](./services/gitlab.md).
- **Pi5 swap and Redis policy (2026-09-15):** enabled 4 GiB NVMe swapfile
  with swappiness 10; increased Redis logical memory to 1 GiB and changed
  eviction to `noeviction` without clearing AOF/data. After GitLab startup,
  swap held 134 MiB but five `vmstat` samples had no swap-in/out churn.
- **MyPocket DNS migration (2026-09-15):** API then worker moved from Pi5
  LAN datastore URLs to `pgbouncer:6432/mypocket` and `redis-prod:6379/1`;
  both passed authenticated probes, API healthy, worker ready, money 200.
- **OpenClaw proxy attribution (2026-09-15):** narrowed trusted overlay CIDR
  to `172.30.0.0/16` after packet capture showed tunnel bridge
  `172.18.0.1` in public XFF. Public and edge routes returned 200; client-
  supplied XFF was overwritten. Real Internet client IP propagation is
  still pending.

- **VM100 disk and unused-cache cleanup (2026-09-15):** grew only VM100
  Proxmox NVMe `scsi0` from 80 to 200 GiB online; grew Ubuntu root ext4
  to 194 GiB usable. Removed an unreferenced Ubuntu installer ISO from
  Proxmox `local` and pruned Docker build cache only (11.53 GB reported;
  VM100 root 58 GiB used, 137 GiB free). No orphan `local-lvm` volume
  existed; documented VM9000 clone template and Compose rollback images
  were retained. After VM restart, `discard=on` became active; guest TRIM
  lowered Proxmox `local-lvm` physical usage from about 83.3 to 66.0 GiB. See
  [disk evidence](./research/gitlab-vm100-preflight-2026-09-15.md).
- **Swarm network audit (2026-09-15):** verified all active Swarm services
  share `homelab-net`; BDS cloudflared stays only on `bds-tunnel-net`.
  MyPocket datastore IP literals were subsequently moved to Docker DNS;
  Mac-native OCR/LLM and OpenClaw trusted-proxy IPs are intentional.
  Documented a phased ingress/data/app segmentation proposal without
  changing broad production network memberships. See
  [network audit](./research/network-segmentation-2026-09-15.md).
- **OCR Redis overlay endpoint (2026-09-15):** added a secret-free durable
  Compose override to Pi5 `redis-prod` retaining its private bridge/data/AOF
  and adding `homelab-net` alias `redis-prod`; changed only OCR proxy
  `REDIS_URL` host/port to `redis-prod:6379/0`. Authenticated `PONG`,
  DB read, task health, native capacity, and public routes passed. MyPocket
  remained untouched as an active-development exception.
- **OCR proxy datastore endpoint (2026-09-15):** changed only the VM100
  Swarm service PostgreSQL URL host/port to `pgbouncer:6432`; private
  `SELECT 1`, task health, native `/capacity`, and public OCR routes passed.
  Redis and Mac-native LAN dependency were unchanged.
- **Family Tree datastore endpoint (2026-09-15):** changed only the VM100
  Swarm service DB URL host/port from Pi5 LAN PgBouncer
  `10.10.0.5:5432` to `pgbouncer:6432`; its own DB client `SELECT 1`,
  task health, and public `/login 200` passed after restart.
- **n8n datastore endpoint (2026-09-15):** replaced its Pi5 LAN PgBouncer
  address `10.10.0.5:5432` with `pgbouncer:6432` on `homelab-net`, without
  changing database/user/password. A private `SELECT 1`, healthy task, and
  public `/healthz 200` passed after the one-service restart.
- **OCR proxy Swarm cutover (2026-09-15):** moved the unchanged VM100 proxy
  image/environment to portless service `macocr-proxy`; Orange Pi now routes
  `ocr.dungxbuif.com` to `tasks.macocr-proxy:8080`. After timed checks and
  Mac native `/capacity 200`, stopped old Compose and closed `18080`.
  Authenticated Redis `PING` from the Swarm task namespace returned `PONG`;
  the earlier `redis-cli -u` URL test failed for both old and new containers
  despite matching credentials. See
  [deployment evidence](./deployments/macocr-proxy-2026-09-15.md).
- **Family Tree Swarm cutover (2026-09-15):** moved the Bun/Next runtime to
  VM100 service `family-tree` with unchanged source/uploads bind mounts and
  environment. Orange Pi file route now targets `tasks.family-tree:3000`.
  Timed public checks and an in-task `SELECT 1` passed before/after stopping
  its old Compose container and closing `18085`. Another canary-time edge
  overlay outage had unresolved ARP in the old Traefik task; a controlled
  task replacement restored public routes. See
  [deployment evidence](./deployments/family-tree-2026-09-15.md).
- **MezonHook Swarm cutover (2026-09-15):** moved the static Nginx app to
  portless VM100 service `mezonhook` and Orange Pi file route
  `tasks.mezonhook:8080`. After timed public checks, stopped its old Compose
  container and closed host port `18084`. The canary exposed a second
  edge-task overlay outage: the old Traefik network namespace had unresolved
  ARP entries while a fresh container on the same node reached overlay apps;
  replacing only `edge_traefik` restored access. See
  [deployment evidence](./deployments/mezonhook-2026-09-15.md).
- **Homepage Swarm cutover (2026-09-15):** deployed `homepage` on VM100 as a
  one-replica, health-checked service on `homelab-net` without a host port.
  Orange Pi file routing now targets `tasks.homepage:80` for both root and
  `www` domains; the old Compose container was stopped after public checks
  and retained for rollback. During the canary, the existing Traefik task
  returned `502` across multiple overlay routes before the homepage route
  changed. Replacing only `edge_traefik` restored them; the underlying overlay
  fault is unconfirmed; subsequent cutovers require paired namespace and
  independent overlay diagnostics before controlled edge-task recovery.
  See [deployment evidence](./deployments/homepage-2026-09-15.md).
- **RelayHub bootstrap deployed (2026-09-14):** added Docker packaging for the
  RelayHub Go bootstrap API, built `homelab/relayhub:bootstrap-20260914`, and
  deployed Swarm service `relayhub` on VM100 with no host port. Added
  `relayhub.dungxbuif.com` to the VPS HostSNI allow-list. Public probes
  returned `/healthz 200`, `/readyz 503`, and `/api/v1/jobs 501`, matching the
  current bootstrap runtime.
- **RelayHub routing normalized:** reverted the experimental Traefik Swarm
  provider and manager-side `edge_docker-socket-proxy` after intermittent
  overlay reachability caused public `502` responses. RelayHub remains a
  portless Swarm service; Orange Pi now routes it through the standard file
  provider target `http://tasks.relayhub:8080`, matching n8n and OpenClaw.
- **CouchDB homelab database added (2026-09-14):** created the `homelab`
  database in Pi5 CouchDB. Existing non-admin CouchDB user remains
  `obsidian_sync`; anonymous access to `homelab` returned `401`. Add explicit
  database `_security` before assigning this database to a specific app.
- **VPS retired services removed:** deleted containers and runtime directories
  for `headscale`, `headscale-ui`, `netbird-server`, `netbird-dashboard`,
  `coturn`, `hbbs`, `hbbr`, and `node-exporter`; purged Tailscale from the
  host.
- **Gateway compose cleaned:** `/root/gateway/docker-compose.yml` now contains
  only `gateway-traefik` and `rathole-server`; stale Coturn/Headscale entries
  and config files were removed.
- **Ports closed:** verified no listeners remain on `3478`, `8080`, `8081`, or
  `21115-21119`, and then removed `9100/tcp` and `41641/udp`. Active VPS
  listeners are `22/tcp`, `80/tcp`, `443/tcp`, and `7000/tcp`.
- **Current VPS role:** public boundary only: Traefik HostSNI allow-list,
  Rathole server, and retained BDS SQL snapshots.
- **Log retention and disk cleanup:** Docker `json-file` logs now rotate at
  `20m x 3` with compression; journald is capped at `200M` with 7-day
  retention. Removed non-edge dev/tool caches (Yarn, pnpm, Go build, npm/nvm,
  Playwright/Prisma, Antigravity, Warp, and VS Code server leftovers). VPS disk
  usage dropped to roughly `3.9G / 38G`.
- **PairDrop route retired:** removed `transfer.dungxbuif.com` from both the
  current Orange Pi Traefik dynamic config source and the live Orange Pi
  `/opt/edge/traefik/dynamic.yml` because PairDrop/Coturn were removed from the
  VPS. Live rollback backup:
  `/opt/edge/traefik/dynamic.yml.bak-20260913-075349-retire-transfer`.
- **NetBird reintroduced on VM100:** deployed NetBird as Swarm services
  `netbird_netbird-server` and `netbird_netbird-dashboard` on `homelab-net`
  with no VM100 host ports. Orange Pi Traefik routes via `tasks.*` DNSRR
  because service VIPs returned `Host is unreachable` from the edge container.
  VPS `gateway-traefik` HostSNI allow-list now includes
  `netbird.dungxbuif.com` and the active Orange Pi hostnames that had drifted
  out of the VPS allow-list. NetBird management, activity, and embedded IdP
  stores now use Pi5 PostgreSQL databases `netbird`, `netbird_activity`, and
  `netbird_idp` via PgBouncer. Public OIDC probe returned `200`.

## v3.2 — 2026-09-13 · Batdongsan local container migration

- **VPS BDS cleanup:** `bds-app`, `bds-prod-db`, the old BDS Docker network,
  local image, `/root/batdongsan`, and stale gateway route configs were removed
  from the Cloud VPS. SQL snapshots remain under `/root/backup-bds`.
- **Database restored to Pi5:** restored VPS snapshot
  `/root/backup-bds/bds_prod_snapshot_20260913_121113.sql` into the Pi5 central
  PostgreSQL database `bds_prod` with dedicated role `bds_user`. Verified
  `listings=31` and `users=4`; snapshot SHA256 is
  `9baa9613153312519e005c72ffc5b8237a2adbdf40e682cb8ba17708fcaf692e`.
- **Container DNS only:** attached Pi5 `postgres` and `pgbouncer` containers to
  the attachable `homelab-net` overlay. BDS build-time DB uses `postgres:5432`
  to avoid PgBouncer build queue timeouts; runtime uses `pgbouncer:6432`.
  No DB host port or Cloudflare Tunnel exposure is used.
- **VM100 app deployed:** built BDS on VM100 in a temporary container attached
  to `homelab-net`, preserving the app's existing static generation behavior.
  Runtime image `homelab/bds-app:vm100-20260913-static` runs as container
  `bds-app` on `homelab-net` and `bds-tunnel-net` with no host port. Internal probes returned
  `GET http://bds-app:3000/api/health 200` and `GET / 200`.
- **Cloudflare Tunnel connector:** `bds-cloudflared` runs on VM100 on
  `bds-tunnel-net` only and targets `http://bds-app:3000`. It must not join
  `homelab-net`; database access remains private through `bds-app`.

## v3.2 — 2026-09-12 · VM100 OpenClaw and n8n redeploy

- **n8n deployed on VM100:** `vm100-n8n` runs
  `docker.n8n.io/n8nio/n8n:stable` at digest
  `sha256:a8c95f75c6fdf65f5f2b7a7b354744eaa1c62bb911b5c00af6499c3f38e4cd32`,
  publishes LAN port `18087`, and uses the Pi5 PostgreSQL database/user `n8n`.
  Secrets live only in `/opt/apps/n8n/.env` on VM100. Local probes returned
  `/healthz 200` and public `https://n8n.dungxbuif.com/ 200`.
- **OpenClaw deployed on VM100:** `vm100-openclaw` runs
  `homelab/openclaw:vm100-20260912`, built from upstream OpenClaw source commit
  `41c45d21`, publishes LAN port `18086`, and uses VM100-local state under
  `/opt/apps/openclaw/`. Qwen/OpenAI-compatible provider credentials and the
  Telegram bot token live only in `/opt/apps/openclaw/.env`; OpenClaw default
  model is set to `openai/qwen/qwen3.6-35b-a3b`. Public
  `https://openclaw.dungxbuif.com/` returned `403`, which confirms the route
  reaches the authenticated gateway.
- **Routing published:** Orange Pi `/opt/edge/traefik/dynamic.yml` and repo
  `migration/traefik/dynamic.yml` now route `openclaw.dungxbuif.com` to
  `10.10.0.31:18086` and `n8n.dungxbuif.com` to `10.10.0.31:18087`.
- **GoClaw remains removed:** `goclaw.dungxbuif.com` still returns `404`; this
  deployment did not restore GoClaw.
- **Operational notes:** VM100 required the `docker-buildx` package to build
  OpenClaw with BuildKit. The build completed but was I/O-heavy; VM100 has no
  swap and should be reviewed for build/runtime headroom.

## v3.2 — 2026-09-12 · Swarm service migration and MyPocket fresh deploy

- **Swarm migration:** `n8n` and `openclaw` were migrated from standalone VM100
  containers with host ports to Swarm services constrained to `vm100-prod` on
  `homelab-net`. Orange Pi Traefik still uses the file provider, but routes now
  target Swarm DNS names (`n8n:5678`, `openclaw:18789`) instead of VM100 host
  ports.
- **OpenClaw public access fix:** configured `gateway.trustedProxies` for the
  Orange Pi/overlay proxy path and added `https://openclaw.dungxbuif.com` to
  `gateway.controlUi.allowedOrigins`.
- **OpenClaw LM Studio provider repair (2026-09-17):** reset stale model
  defaults, registered the custom `lmstudio` provider at
  `https://llm.dungxbuif.com/v1`, set primary model
  `lmstudio/qwen/qwen3.6-35b-a3b`, and saved the current LM Studio API-key
  profile for agent `main`. Older malformed setup profiles were removed. The
  public route and `/healthz` are live; the OpenClaw Model Setup UI may still
  require selecting the saved `lmstudio` sign-in and refreshing connections
  because LM Studio does not expose an app-guided starter model.
- **OpenClaw Telegram DM repair (2026-09-17):** Telegram polling was already
  receiving updates for `@dungxbuif_openclaw_bot`, but all DMs were dropped
  because `channels.telegram.dmPolicy=open` lacked `allowFrom=["*"]`. Added the
  allow-list wildcard and rolled only the `openclaw` Swarm service; the
  provider starts without the prior DM-drop config warning.
- **Educates renderer repair (2026-09-17):** the LAN lab returned
  `Renderer Failed` because the generated workshop config had no active pages
  and the Docker session had no published content artifact. Added the Hugo
  pathway/modules config, published content to VM100's local
  `educates-local-registry`, redeployed from `workshop.published.yaml`, and
  firewalled the registry so only the workshop subnet can pull from it.
- **Educates removed (2026-09-17):** removed the generated Educates skeleton
  after deciding to use the upstream Kubernetes fundamentals course later.
  Deleted VM100 workshop/runtime containers, the local content registry,
  workshop volumes/networks, `/opt/apps/educates-lab`, `DOCKER-USER` rules for
  ports `10081` and `5000`, the Pi5 Traefik `educates` router/service, and the
  repo migration/doc artifacts.
- **MyPocket fresh deploy:** built `homelab/mypocket-api:vm100-20260912-okb335cb4`
  and `homelab/mypocket-web:vm100-20260912-okb335cb4` from the current
  MyPocket source, reset the Pi5 PostgreSQL `mypocket` schema, flushed the
  MyPocket Redis DB index, and deployed Swarm services `mypocket-api`,
  `mypocket-worker`, and `mypocket-web` on VM100.
- **Routing:** `money.dungxbuif.com` now routes to `mypocket-web:80` over
  `homelab-net`; public probes returned `/api/v1/health/live 200`,
  `/api/v1/health/ready 200`, and `/ 200`.

## v3.2 — 2026-09-11 · VM100 Swarm worker onboarding intent

- **Completed 2026-09-12:** VM100 (`10.10.0.31`, hostname `vm100-prod`) joined
  the existing Docker Swarm as a worker. The Swarm manager (`rpivn`, Pi5
  `10.10.0.5`) now reports `vm100-prod` as `Ready` and `Active`.
- **Intent:** VM100 can later run production app workloads behind the Orange Pi
  Traefik edge using Swarm service labels.
- **Topology decision:** Do not create a separate single-node Swarm on VM100 by
  default. The intended cluster is the existing Pi5 manager + Orange Pi worker
  Swarm; VM100 should join that cluster as an additional worker.
- **Scope:** This step installs/enables Swarm membership only. It does not move
  MyPocket, does not redeploy GoClaw, and does not migrate existing VM100
  containers into Swarm services yet.
- **Verification:** VM100 `docker info` reports `Swarm=active`; Pi5
  `docker node ls` lists `rpivn` as manager/leader plus `orangepizero3` and
  `vm100-prod` as workers. Existing VM100 containers and Orange Pi file-provider
  routes were left unchanged.

## v3.2 — 2026-09-11 · Current docs audit and archive cleanup

- **Current docs reconciled:** Root `index.md`, `docs/MAIN.md`,
  `docs/INDEX.md`, `docs/PI.md`, and `docs/MAC.md` now describe the live
  topology: VPS `gateway-traefik` -> Rathole -> Orange Pi `edge_traefik`,
  VM100 production compute, Pi5 datastore/Swarm manager, and Mac dependency
  host.
- **New current docs:** Added `docs/VM100.md` for the VM100 production services
  and `docs/PROJECTS.md` for local project workspace layout.
- **Caddy-era content archived:** The superseded Orange Pi Caddy migration plan
  and helper scripts were moved under `docs/archived/edge-caddy-era/`.
  `migration/` now holds only current Traefik/Rathole/AdGuard deployment source.
- **Retired services removed from current docs at that point:** GoClaw,
  OmniScan bot, n8n, GitLab web/git routes, Caddy edge, and VPS Nginx were
  treated as historical or explicitly retired unless mentioned in dated
  changelog entries. n8n was later redeployed on VM100 on 2026-09-12; GoClaw
  remains removed.
- **Explicit exceptions:** MyPocket remains outside VM100 migration and stays at
  `/Users/dungxbuif/workspace/MyPocket/`; `money.dungxbuif.com` may remain a
  known 502 while the app is under development.

## v3.2 — 2026-09-06 · GoClaw LAN SSRF allowlist for homelab OCR

> Historical note. GoClaw public routing and runtime data were later removed on
> 2026-09-11; retain this entry only as the decision trace for the old GoClaw
> host.

- **GoClaw native SSRF allowlist:** Added `GOCLAW_SSRF_ALLOWED_CIDRS=10.10.0.0/24` to `/Users/dungxbuif/production/goclaw-host/env.example` and restarted `com.dungxbuif.goclaw-native`. This matches the documented physical LAN segment for Mac/Pi/edge services and lets GoClaw reach LAN-routed services such as OCR when they resolve through the homelab edge path.
- **Scope decision:** Do not broadly allow all RFC1918 ranges by default. `10.10.0.0/24` is the documented physical LAN; `172.30.0.0/16` is the Swarm overlay and should normally be reached through the documented Caddy/domain routes unless a direct overlay path is explicitly required. `100.64.0.0/10` is the Headscale tailnet and is not in GoClaw's current hard-blocked SSRF CIDR list.
- **Separate gate:** Shell `curl -X POST` remains controlled by GoClaw shell policy, not SSRF. The SSRF allowlist only relaxes destination-network validation for supported HTTP/tool paths.

## v3.2 — 2026-08-17 · Edge ingress reconciliation discovery

> Historical reconciliation note. This entry captured an intermediate discovery
> state before the September Traefik cleanup. The current live edge is VPS
> `gateway-traefik` -> Rathole -> Orange Pi `edge_traefik`; do not use this
> entry as a current runbook.

- **Documentation drift corrected:** the VPS was migrated from Nginx to
  `gateway-traefik`. The live security gate is TCP router
  `rathole-passthrough` and its `HostSNI(...)` rule. Editing `dynamic.yml`
  auto-reloads through Traefik's file provider; `nginx.conf` and
  `docker compose restart nginx-gateway` are obsolete playbook instructions.
- **Superseded service-export scope:** this entry still mentions Pi5 Caddy.
  Current service export uses Orange Pi Traefik dynamic config and the VPS
  Traefik HostSNI allow-list.
- **Security follow-up recorded:** Cloudflare API tokens, PostgreSQL passwords,
  and the Rathole default token remain plaintext in existing deployment
  configuration. Rotate and move them to a secret manager or SOPS; new
  automation must use environment-provided credentials and must not add secrets
  to repository files.

## v3.1 — 2026-08-17 · Orange Pi Zero 3 edge migration

> Historical migration record. The later current edge is Orange Pi
> Traefik+Rathole+AdGuard; Caddy references in this section are retained only to
> explain how the edge migrated.

- **Orange Pi Zero 3** (`10.10.0.2`, Armbian Bookworm, ARM64, 1GB RAM) brought online as the new **TLS edge gateway** via Docker Swarm (Pi5=manager, orange-pi=worker). Migrated **Caddy+Rathole+AdGuard** off the Pi5 onto the orange-pi as Swarm services, leveraging an attachable overlay network `homelab-net` (172.30.0.0/16) so orange-pi Caddy can still resolve Pi5 datastore containers (`rustfs`, `docker-registry`, `librespeed`, `n8n`, `pgadmin`, `goclaw`, `couchdb`, `gitlab`) by Docker DNS name without publishing host ports.
- **Pi5** now operates as a **datastore-only node** (Postgres, PgBouncer, RustFS, Redis, Registry, LibreSpeed, n8n, pgAdmin, CouchDB, GitLab, GoClaw, monitoring stack). Containers were attached to the overlay via `docker network connect` (zero downtime — no recreate). Pi5 remains the **Swarm manager**.
- **Rathole tunnel cutover:** stopped Pi5 rathole client (`restart:always`→`no` then stop), orange-pi rathole stabilized as sole client (VPS server drops previous control channel on same token — last-connect-wins). Public ingress verified 200 for all 11 routes.
- **AdGuard DNS cutover:** Stopped Pi5 AdGuardHome; orange-pi AdGuardHome running on `10.10.0.2:53` with `bind_hosts: [10.10.0.2]` and `*.dungxbuif.com → 10.10.0.2` rewrite (LAN clients sent to local Caddy). **Pending:** MikroTik DHCP DNS change from `10.10.0.5`→`10.10.0.2` (operator Winbox). LAN clients currently using `1.1.1.1` fallback until DHCP updated.
- **Headscale** nameserver updated on VPS: `10.10.0.5`→`10.10.0.2`.
- **Pi5 cleanup:** Caddy+Rathole+AdGuard stopped permanently (`restart` disabled). Dead Caddyfile routes remain (uptime-kuma, netdata, postgres) — operator will clean.
- **CF_API_TOKEN** was stale in `local_vars.json` (old `__GHn...` returned 403 from Cloudflare); updated to the live token from Pi5 caddy env. Docker installed on orange-pi (`29.7.2`). NOPASSWD sudo temp removed.
- **Docs:** index.md topology updated; PI.md and MAIN.md edge roles updated. Plan + scripts at `docs/migration_orange_pi_edge.md` and `migration/`.

## v3.0 — 2026-08-17 · Mac mini consolidation + Proxmox AWS lab repurpose

- **Architecture version bump to v3.** Migrated all user-facing production workloads off the 3-node Proxmox K8s cluster (`k8s-cp-1/2/3`, VIP `10.10.0.30`) onto the **Mac mini** (`10.10.0.10`, Apple Silicon, Docker Compose). The Pi5 (`10.10.0.5`) remains the sole TLS edge (Caddy, Cloudflare DNS-01 wildcard) and now also hosts **Redis-prod** for the Mac stack. The K8s cluster is retired; Proxmox (`10.10.0.20`) is repurposed as a self-hosted **AWS practice lab** (LocalStack / eksctl / k3s).
- **Mac mini production stack** (`~/production/`): three containers on a bridge network `homelab` — `homelab-homepage` (`:18081`, registry image, amd64 via Rosetta), `homelab-macocr-proxy` (`:18080`, built locally), `homelab-omniscan-bot` (no host port, Mezon bot). Spec: [MAC.md](./MAC.md). Runbook: `~/production/README.md`.
- **Native OCR bridge:** the proxy reaches the macOS-host Swift OCR engine (`mac-ocr-native :8787`) via `host.docker.internal`. Verified that `network_mode: host` is a no-op on Docker Desktop for macOS (Linux VM cannot see the macOS host) — must use bridge + `host.docker.internal`. Documented in [MAIN.md](./MAIN.md) bug registry #7.
- **AI agent disabled** on omniscan-bot via a build-time `awk` patch stubbing `handleThreadQuestion()` (source repo `~/workspace/mac-ocr/` left untouched). Only `*ocr` works. Disabled message baked into the binary.
- **Redis-prod on Pi5** (`/ssd-data/infra/redis-prod/`, `redis:7.2-alpine`, bind `0.0.0.0:16379`, auth, AOF, 256mb LRU) — deliberate portless-principle exception so Mac containers can reach it over LAN. Documented in [PI.md](./PI.md).
- **DB password URL-encoding:** the `/` in the Postgres password broke the stricter `net/url` parser in freshly built images (legacy K8s `v1.0.2` tolerated it). URL-encoded as `%2F` in `DATABASE_URL`. Documented in [MAIN.md](./MAIN.md) bug registry #8.
- **Caddy cutover (Pi5):** live `/ssd-data/infra/Caddyfile` updated to route `dungxbuif.com`→`10.10.0.10:18081` and `ocr.dungxbuif.com`→`10.10.0.10:18080`; `grafana.dungxbuif.com` and the K8s-only routes (`localstack/longhorn/argocd/traefik/portainer`) retired. Backup at `/ssd-data/infra/Caddyfile.bak-20260817190337`. Source: `~/production/caddy/Caddyfile.pi5.cutover`. Verified `dungxbuif.com`/`ocr.dungxbuif.com`→200, `grafana`→404.
- **K8s cleanup:** deleted ArgoCD `homepage-prod` Application (stop GitOps self-heal) and the app namespaces `homepage-prod`, `homepage-dev`, `macocr`, `omniscan`, `redis`, `localstack`, `monitoring`, `gitlab-runner`. Remaining on K8s: `argocd`, `traefik`, `longhorn-system`, `kube-system` (cluster infra — to be destroyed with the Proxmox VMs separately).
- **GitLab on Pi5** stopped temporarily (operator decision).
- **Docs restructure (this entry):** archived the K8s-era docs into [./archived/k8s-v2/](./archived/k8s-v2/) (`docs/k8s/`, `monitoring/`, `2026-05-29_k8s_proxmox_iac_design.md`, `PROXMOX.md`→`PROXMOX.k8s.md`, `goclaw_implementation_plan.md`, OCR benchmark reports). Rewrote the core docs to v3: [index.md](../index.md), [MAIN.md](./MAIN.md), [INDEX.md](./INDEX.md), [PROXMOX.md](./PROXMOX.md); added [MAC.md](./MAC.md) and [archived/INDEX.md](./archived/INDEX.md); updated [PI.md](./PI.md) (Redis-prod, Mac bridge, retired routes). Note: pre-2026-08-17 entries below contain links to the old `./k8s/...` and `./monitoring/...` paths — those files have moved to `./archived/k8s-v2/`. The old `./PROXMOX.md` (K8s cluster) is now `./archived/k8s-v2/PROXMOX.k8s.md`; `./PROXMOX.md` is the new AWS-lab version. See the archived index.

## 2026-08-04

- **Headscale & Tailnet Mesh Migration (WireGuard Decommissioned)**: Decommissioned and cleaned up the legacy `wg0` WireGuard interfaces across the Cloud VPS (`103.82.21.202`) and Raspberry Pi 5 (`10.10.0.5`). Deployed Headscale Control Server (`headscale/headscale:v0.25.0`) on the Cloud VPS (`103.82.21.202`) behind Nginx direct SSL termination (`https://headscale.dungxbuif.com`) with embedded DERP relay server on port `3478/udp` and MagicDNS domain `homelab.net`. Enrolled Raspberry Pi 5 (`100.64.0.1`, Subnet Router for `10.10.0.0/24`), Cloud VPS (`100.64.0.2`), and Proxmox VE Hypervisor (`100.64.0.3`) into the P2P Tailnet mesh. Verified sub-5ms P2P direct latency and full cross-node access over Tailnet.

## 2026-08-03

- **PairDrop & Coturn Direct VPS Deployment**: Deployed PairDrop (`lscr.io/linuxserver/pairdrop:latest`) and Coturn STUN/TURN Server (`coturn/coturn:4.6.2`) directly on the Cloud VPS (`103.82.21.202`). Copied wildcard TLS certs (`*.dungxbuif.com`) to `/root/gateway/certs/` on the VPS to enable **direct SSL termination on Nginx Gateway** (`127.0.0.1:8443`), eliminating any hairpin routing back to the Raspberry Pi 5 at home. PairDrop web ingress is served via `https://transfer.dungxbuif.com` with Coturn STUN/TURN on port `3478` (TCP/UDP).

## 2026-07-30

- **IT-Tools Deployment**: Deployed IT-Tools (`corentinth/it-tools:latest`) as a portless Docker container service on the Raspberry Pi 5 (`10.10.0.5`) running inside `proxy_net`. Added ingress routing block for `tools.dungxbuif.com` in Caddyfile (`reverse_proxy it-tools:80`), and added `tools.dungxbuif.com` to the Nginx SNI and HTTP host whitelists on the Cloud VPS gateway (`103.82.21.202`) for public internet accessibility.

## 2026-07-15

- **RustFS Storage**: Created a new S3-compatible bucket `whiteboard` on the RustFS object storage running on the Raspberry Pi 5. Configured a dedicated user/access key `whiteboard` with secret key `<WHITEBOARD_MINIO_SECRET_KEY>` and attached a custom read/write policy `whiteboard-policy` scoped strictly to the `whiteboard` bucket. Added `WHITEBOARD _MINIO_ACCESS_KEY` to `local_vars.json` as the local source of truth.

## 2026-07-09

- **Kubernetes/AWS Lab**: Added a LAN-only LocalStack deployment for AWS SAA practice under [iac/k8s/localstack/README.md](../iac/k8s/localstack/README.md). The deployment uses namespace `localstack`, ClusterIP service, Traefik Ingress host `localstack.dungxbuif.com`, Longhorn PVC persistence, and no NodePort/direct LoadBalancer. Lab endpoints are `https://localstack.dungxbuif.com` from LAN clients, `http://localstack.localstack.svc.cluster.local:4566` inside K8s, and `http://localhost:4566` through `kubectl port-forward` as fallback. Docker-in-Docker and privileged mode are disabled by default; Lambda/container-runtime behavior must be enabled only by a separate security decision. The image is pinned to `localstack/localstack:3.8.1` because current latest/stable images require `LOCALSTACK_AUTH_TOKEN`.

## 2026-07-08

- **CouchDB/Obsidian Sync**: Deployed CouchDB on the Raspberry Pi 5 Docker stack as a portless `proxy_net` service. Added Caddy routing for `couchdb.dungxbuif.com` and `sync-db.dungxbuif.com`, added the same host whitelist entries on the Cloud VPS Nginx gateway, and created a dedicated `obsidian_vault` database with a non-admin sync user for Obsidian vault replication. Runbook: [COUCHDB_OBSIDIAN_SYNC.md](./COUCHDB_OBSIDIAN_SYNC.md).
- **VPN/WireGuard**: Resolved the SSH inaccessibility issue on the Raspberry Pi when connected to the VPN from outside the LAN. Added `PersistentKeepalive = 25` to `/etc/wireguard/wg0.conf` on the Pi and restarted the `wg0` interface. This prevents the home router from closing the UDP NAT session mappings, ensuring the Pi remains reachable from all VPN peers.

## 2026-07-04

- **Consolidation**: Consolidated root files (`AGENT.md`, `README.md`, and `index.md`) into a single unified `index.md` serving as the gateway and infrastructure overview for the Homelab repository. Removed deprecated `AGENT.md` and `README.md` files and updated all relevant references across the workspace.

## 2026-06-25

- **Database/PgBouncer**: Configured a centralized connection pooler (**PgBouncer**) running in `transaction` pool mode, exposed on port `5432` on the Pi 5. Kept the raw `postgres` container hidden inside the Docker `proxy_net` network to enforce access isolation.

## 2026-06-24

- **DNS/AdGuard Home**: Added multiple resilient upstream resolvers (`https://dns.google/dns-query`, `https://cloudflare-dns.com/dns-query`, `1.1.1.1`, `8.8.8.8`) and bootstrap DNS servers to `AdGuardHome.yaml` on the Raspberry Pi 5. This resolved local network DNS resolution dropouts caused by timeouts and `unexpected EOF` connection failures when querying the single previous DoH upstream (`https://dns10.quad9.net/dns-query`).

## 2026-06-23

- **DNS**: Disabled `DNSStubListener` of `systemd-resolved` on Raspberry Pi 5 to free port 53 for AdGuard Home.
- **Restructure**: Restructured the documentation directory to follow the Open Knowledge Format (OKF) standard (v0.1) and translated all contents from Vietnamese to English. Created root and subdirectory indexes: [INDEX.md](./INDEX.md), [k8s/INDEX.md](./archived/k8s-v2/k8s/INDEX.md), [monitoring/INDEX.md](./archived/k8s-v2/monitoring/INDEX.md). Converted concepts: [2026-05-29_k8s_proxmox_iac_design.md](./archived/k8s-v2/2026-05-29_k8s_proxmox_iac_design.md), [CONTEXT.md](./CONTEXT.md), [MAIN.md](./MAIN.md), [MIKROTIK.md](./MIKROTIK.md), [PI.md](./PI.md), [PRE_REQUIRE.md](./PRE_REQUIRE.md), [PROXMOX.md](./PROXMOX.md), [k8s/CICD.md](./archived/k8s-v2/k8s/CICD.md), [k8s/DB.md](./archived/k8s-v2/k8s/DB.md), [k8s/DB_INVENTORY.md](./archived/k8s-v2/k8s/DB_INVENTORY.md), [k8s/LONGHORN_CONFIG_REVIEW.md](./archived/k8s-v2/k8s/LONGHORN_CONFIG_REVIEW.md), [k8s/RECOVERY_GUIDE.md](./archived/k8s-v2/k8s/RECOVERY_GUIDE.md), [monitoring/README.md](./archived/k8s-v2/monitoring/README.md). Added the official specification reference: [OKF_SPEC.md](./OKF_SPEC.md).

- **Fix**: Resolved the K8s DNS query loops for `kubernetes.nccsoft.office` by:
   - Replacing the `nccsoft.office` search domain with `lan` in Netplan configs on K8s nodes `k8s-cp-1`, `k8s-cp-2`, `k8s-cp-3` and running `netplan apply`.
   - Updating `iac/terraform/main.tf` to explicitly specify `searchdomain = "lan"` to prevent future regressions.
   - Modifying `/etc/resolv.conf`, `/etc/hosts`, and `/etc/postfix/main.cf` on the Proxmox host (`10.10.0.20`) to replace `nccsoft.office` with `lan`.

## 2026-06-06

- **Database**: Centrally hosted all PostgreSQL databases in the lab on Raspberry Pi 5 (`postgres.dungxbuif.com`).

## 2026-06-03

- **CI/CD**: Replaced self-hosted GitLab on Pi 5 with GitHub Actions (ARC) + ArgoCD to conserve RAM.
- **Restructure**: Moved sub-documentation files (`MAIN.md`, `PI.md`, `CONTEXT.md`) into `/docs/`.
- **Gateway**: Renamed root `README.md` to `AGENT.md` as the mandatory AI agent gateway.
- **Storage**: Selected Longhorn v1.7.x for manual installation (replica count 2).
- **Ingress**: Established Traefik Ingress on K8s VIP `10.10.0.30` with Caddy as the main entry proxy.
- **Topology**: Joined nodes `k8s-cp-2` and `k8s-cp-3` to cluster and installed Cilium CNI.
