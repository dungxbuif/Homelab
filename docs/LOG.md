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

## 2026-10-21 - Runtime audit continuation

- **VPS HostSNI incident forensic result:** compared the live, known-good and
  retained failed gateway files, checked the Traefik bind mount and watcher,
  and reviewed the incident window without changing the VPS. The files differ
  by exactly one allow-list term and both parse, so the evidence points to an
  unsafe live file-provider mutation rather than malformed YAML. The exact
  historical watcher event is not recoverable from retained logs; S2 is now
  partial while the guarded edit path is implemented. See [VPS HostSNI
  incident](./deployments/vps-hostsni-incident-2026-10-21.md).
- **Homepage CI secret boundary tightened:** changed the Mezon webhook input
  from a masked text variable to a protected GitLab file variable, so the
  release job reads the existing webhook only as a file-backed runtime value.
  Live enrollment remains pending; no secret was transmitted in this change.
- **Public GitHub credential audit:** fetched the public Homelab repository
  read-only and scanned its two refs/13 reachable commits for token, private
  key, webhook, bot-token, JWT and cloud-key patterns. No real credential was
  found; remaining matches were deprecated placeholders. S1 remains open until
  previously exposed credentials are revoked or rotated at their issuers. See
  [GitHub credential exposure audit](./deployments/github-credential-exposure-audit-2026-10-21.md).
- **B9 native pull transport:** the backup adapters still used Pi5 `docker exec`
  for database export even after VM100 took over Restic retention. Added the
  source contract for optional VM100 network transports, retaining Pi5 mode as
  the default rollback path. No runtime or credential changed. See [native
  pull transport](./deployments/backup-native-pull-transport-2026-10-21.md).
- **Native pull verification:** the new PostgreSQL/CouchDB transport contracts
  and Python compilation pass. The workstation-wide backup suite still reports
  pre-existing macOS fixture issues (`flock`, missing `jinja2`, and unenrolled
  Pi health fixtures); no runtime backup service was changed.

- **Image update watch:** added VM100 Diun in notify-only mode with a pinned
  image digest, read-only Docker socket, no published ports, and `0.25 CPU /
  256 MiB` limits. It checks running-container images every 12 hours and sends
  Mezon warnings without pulling or restarting workloads. See
  [Diun image watch](./deployments/diun-image-watch-2026-10-21.md).
- **GitLab CI approval boundary:** added a protected manual production job for
  the catalog-approved Homepage digest. The job uses the existing fixed
  forced-command account on Pi5, pinned host identity, serialized release
  execution, and the existing Mezon receipt path; it fails closed until the
  protected GitLab file variables and production environment are enrolled. See
  [GitLab CI Homepage approval](./deployments/gitlab-ci-homepage-approval-2026-10-21.md).
- **Backup failure reconciliation:** correlated the recent database and
  monitoring-drift failures with their journals. The database failure was an
  older deployed-script syntax error and the monitoring failure was the
  pre-repair missing-helper invocation; corrected runs succeeded afterward.
  A fresh health run passed with VM100 at `81%` used and Pi5 at `35%` used,
  both locks free and no failed systemd units. See
  [backup failure reconciliation](./deployments/backup-failure-reconciliation-2026-10-21.md).
- **PostgreSQL collation warning resolved:** refreshed collation metadata and
  reindexed only the maintenance database `postgres` after the read-only audit
  found its stored version at `2.41` while the runtime was `2.36`. All
  application databases remained at `2.36` and returned `SELECT 1`; no service
  restart was required. See
  [PostgreSQL collation reconciliation](./deployments/postgres-collation-reconciliation-2026-10-21.md).

- **Pi5 backup cgroup enforcement:** installed a root-owned, class allow-listed
  systemd wrapper and argument-specific sudoers rules. The Pi executor now
  defaults to transient scopes with `CPUQuota=100%`, `MemoryMax=1G`, and
  `IOWeight=50`; explicit `configs` probe exited 0 with payload output
  suppressed. Portable mode remains the rollback path. Pi5 resource-cap tests
  and scheduler contract tests pass.

- **OpenClaw resource canary:** bounded the VM100 Swarm service at `1 CPU/2 GiB`
  with `stop-first`, preserving its persistent state/auth/workspace mounts and
  rollback policy. The update completed, the new task became healthy, and the
  public route plus `/healthz` and `/readyz` returned 200. A brief 502 during
  warm-up cleared without rollback. See
  [OpenClaw resource canary](./deployments/openclaw-resource-canary-2026-10-21.md).
- **MyPocket API resource canary:** bounded only `mypocket-api` at `1 CPU/1 GiB`
  with `stop-first`; the worker remains uncapped pending queue metrics. The API
  task became healthy and `/api/v1/health` returned 200 after a brief warm-up
  502. See [MyPocket API resource canary](./deployments/mypocket-api-resource-canary-2026-10-21.md).
- **RelayHub resource canary:** added persistent Compose limits of `1 CPU/1 GiB`
  to both API and worker. Compose recreated the dependency containers while
  retaining the NATS volume; all four containers became healthy and public
  `/readyz`, `/healthz`, and `/docs/` returned 200. See
  [RelayHub resource canary](./deployments/relayhub-resource-canary-2026-10-21.md).
- **Family Tree and MezonHook resource canaries:** capped Family Tree at
  `0.50 CPU/512 MiB` with `stop-first` and MezonHook at `0.50 CPU/512 MiB`
  with `start-first`. Their route checks returned 200 and their images,
  networks, mounts, and environment were preserved. See
  [Family/MezonHook canary](./deployments/family-mezon-resource-canary-2026-10-21.md).
- **Worker/control-plane resource canaries:** capped `mypocket-worker` and
  `n8n-runners` at `0.50 CPU/512 MiB`, and NetBird server at `1 CPU/1 GiB`
  with `stop-first`. Their tasks remained running; the NetBird dashboard stayed
  HTTP 200. Stateful RelayHub dependencies now also use `1 CPU/1 GiB` with
  volumes retained.
- **Whiteboard resource canary:** added persistent CPU limits to all five
  Compose containers without rebuilding images. Backend, feature-worker,
  collab, MCP and frontend became healthy; public `/` and `/healthz` returned
  200. See [Whiteboard resource canary](./deployments/whiteboard-resource-canary-2026-10-21.md).
- **CouchLoom resource reconciliation:** corrected source/runtime drift by
  bounding PostgreSQL at `1 CPU/2 GiB` and Ollama at `2 CPU/4 GiB` with equal
  memory-swap limits. All CouchLoom containers stayed healthy and volumes were
  preserved; its intentional lack of a public route remains documented. See
  [CouchLoom reconciliation](./deployments/couchloom-resource-reconciliation-2026-10-21.md).
- **VM100 resource inventory closeout:** the final live query found no running
  container with an unset CPU or memory limit. The orphan BDS tunnel was removed
  after confirming there was no BDS origin container, service, or source tree;
  its empty private network was removed too. See
  [resource inventory closeout](./deployments/vm100-resource-inventory-2026-10-21.md).
- **NetBird dashboard resource canary:** capped the stateless dashboard at
  `0.50 CPU/512 MiB` with `start-first`. The Swarm update completed and the
  public dashboard returned HTTP 200. The stateful NetBird server was left
  unchanged. See [NetBird dashboard resource canary](./deployments/netbird-dashboard-resource-canary-2026-10-21.md).

- **Backup and capacity check:** VM100 has no failed `homelab-backup` units and
  retains `39G` free (`81%` used). The constrained Docker maintenance service
  completed with `Result=success`; there are no Dead containers. The stopped
  Compose-era `vm100-family-tree-app` container and its dangling `oven/bun`
  image were removed after verifying that the active Swarm `family-tree`
  service remained healthy and its bind-mounted source/uploads were untouched.
- **AI model audit:** OpenClaw, Whiteboard and MyPocket API still select
  `DeepSeek-V4.1-Flash`. `mypocket-worker` still reports the historical
  `qwen/qwen3.6-35b-a3b`; the source selector map is already aligned, but the
  Swarm service spec can only be changed from the Pi5 manager. No speculative
  worker restart was performed.
- **VM100 host identity cleanup:** replaced the retired `k8s-cp-1` alias in
  `/etc/hosts` with `127.0.1.1 vm100-prod`, preserving a timestamped backup at
  `/etc/hosts.bak-k8s-alias-20261020-205035`. `sudo` no longer warns,
  systemd reports `running`, and the running-container count stayed at `34`.
- **Backup health recheck:** manually started `homelab-backup-health.service`
  after Docker cleanup. It exited successfully with a free lock, no failed
  backup units, and the configured timers all enabled/active. Config backup is
  scheduled for `2026-10-21 06:00 UTC`; weekly deep verification is scheduled
  for `2026-10-25 02:00 UTC`. The health output includes the remote Pi5
  database/RustFS markers, so their local absence from VM100's `.state` folder
  is expected.
- **Retired build-image cleanup:** removed unreferenced `node:26.7.0-bookworm`
  and `node:24-bookworm` images (about `3.3G` total). No running or stopped
  container referenced either image; production/rollback images were preserved.
  VM100 increased from `39G` to `42G` free (`79%` used), with no unhealthy
  containers after the cleanup.
- **Docker volume audit:** removed 17 anonymous 4-KiB volumes and one additional
  empty Docker metadata volume. Retained the remaining non-empty dangling
  volumes: two PostgreSQL data directories created on 2026-10-19, the
  `workshop-files` registry metadata/layers volume, and the named
  `mypocket-prod-backups` volume containing the pre-migration dump. No database
  or registry volume was deleted as part of cleanup.
- **Proxmox VM recovery audit:** read-only API verification confirmed VM100 is
  running with the documented `6 vCPU / 16 GiB / 200 GiB` allocation; VM IDs
  101 and 102 are absent and only template 9000 remains. VM100 has one
  pre-Docker-upgrade snapshot (`pre-docker-ce-20261014`) but no `vzdump` backup.
  The only backup-capable `local` storage has about `89.8G` free while the
  guest disk is `200G` and the guest uses about `153G`, so no same-storage
  vzdump was started. B3 remains open until a separate NAS/PBS/attached target
  is available.
- **Automation test runtime:** made `audit-runtime.sh` honor `PYTHON_BIN` and
  updated the policy contract test to pass its active interpreter. The pinned
  execution environment remains the default; local tests no longer fall back to
  a system Python missing `PyYAML`/`jsonschema`. Route, network-drift, policy,
  evidence, host-observer and runtime-evidence tests now pass (`46` tests).
- **Tracked-file credential audit:** `automation/scripts/check-secrets.sh`, the
  secret-output scan and toolchain-security tests pass. This verifies the
  current tracked tree only; it does not clear the open S1 finding for secrets
  that may already exist in public Git history and still require rotation.
- **Deploy contract test runtime:** aligned `verify-deploy.sh` and its contract
  tests with the same `PYTHON_BIN` execution-environment boundary used by the
  runtime audit. Deploy/policy contract tests now pass (`11` tests), including
  the approved Homepage digest and rejection of the non-release-ready Family
  Tree service. This validates the gate only; it does not enroll a generic
  production deploy workflow.
- **Cross-platform image-scan tests:** `scan-image.sh` now resolves GNU
  `timeout`/Homebrew `gtimeout` when available. The pinned execution image
  still enforces the configured start timeout; macOS local tests use the
  scanner's direct start path only when neither utility exists. Full automation
  discovery now passes: `121` tests plus `29` Ansible tests.

## 2026-10-20 - VM100 capacity protection (in progress)

- **Backup health runtime calibration:** historical `databases` runs completed
  in roughly 92 to 104 minutes, while health used a 30-minute active-unit
  limit. Raised the databases limit to two hours on VM100 and Pi5 and added a
  regression test for a 5,600-second run. This removes the false overlong
  failure without changing the four-hour SSH safety timeout; the current run
  remains allowed to finish and will be checked at idle.

- **Daily backup health summary:** the scheduled health service now sends a
  successful one-line Mezon notification in addition to failure alerts. The
  script defaults to quiet success for ad-hoc checks; only the systemd service
  enables `BACKUP_HEALTH_NOTIFY_SUCCESS=true`.
- **Backup schedule separation:** `database-instances` was moved from 01:30 to
  03:00 Asia/Ho_Chi_Minh (20:00 UTC). The previous 30-minute offset overlapped
  the normal 92-104 minute `databases` run and caused lock contention; the
  timer is now separated by two hours.

- **OpenClaw provider verification:** verified the live VM100 task uses the
  existing `fpt-deepseek` provider at `https://token-api.fpt.ai/v1` with
  default model `DeepSeek-V4.1-Flash`. The credential remains runtime-only via
  `OPENAI_API_KEY`; no secret was written to docs or emitted in verification
  output. Host/container config matched, so no restart or unrelated service
  change was made. See
  [OpenClaw DeepSeek verification](./deployments/openclaw-deepseek-2026-10-20.md).
- **AI model audit and rollout:** audited production AI selectors with values
  redacted. Only `mypocket-api` used `DeepSeek-V4-Flash`; its server-side
  selector now uses `DeepSeek-V4.1-Flash`. The provider catalog, API health and
  docs probes passed. `mypocket-worker` uses Qwen and was left unchanged.
  OpenClaw was subsequently switched to the verified FPT DeepSeek credential
  and now uses `DeepSeek-V4.1-Flash`. `whiteboard-backend` uses a separate DeepSeek endpoint with
  `deepseek-chat`/`deepseek-reasoner`; its target-model compatibility is not
  assumed and remains a separate verification item. Stirling's paused network
  migration was first rolled back to its known-good state, then completed with
  `stop-first` after an H2/config backup. Stirling is now healthy on
  `edge-http-net` and its public probe returns HTTP 200.
- **NetBird route repair:** corrected the remaining backend and h2c routers from
  the retired `tasks.netbird-server` name to the live Swarm service DNS name
  `tasks.netbird_netbird-server`; restarted the actual Pi5 Traefik container
  after backing up its dynamic config. Public root/API/backend probes now
  return 200/401/404 rather than 502.
- **VM100 maintenance verification:** ran the constrained Docker maintenance
  service successfully. It found zero eligible Dead tasks, reclaimed no
  protected data, and left 32 running task IDs unchanged; VM100 remains at 52G
  free / 74% used. An older lock-permission failure remains in the journal, but
  the latest run exited 0.
- **Backup control-flow verification:** health reporting, scheduler contract,
  runner contract and retention-gate tests passed locally. Drive restore remains
  unverified and therefore stays open in the backlog.
- **Whiteboard AI rollout:** switched `whiteboard-backend` from the separately
  failing DeepSeek endpoint to the verified FPT endpoint and set both fast and
  reasoning selectors to `DeepSeek-V4.1-Flash`. Container and `/healthz` passed;
  real business inference remains pending UAT.
- **Whiteboard network cleanup:** removed the frontend's `homelab-net`
  membership, persisted `edge-http-net` in its Compose file, recreated only the
  frontend, and verified healthy/public HTTP 200. Compose backup:
  `/opt/apps/whiteboard/docker-compose.prod.yml.bak-frontend-edge-20261020-153520`.
- **KubeKosh network cleanup:** moved the LAN-only learning container from
  `homelab-net` to `edge-http-net`, recreated it with its persistent data
  untouched, and verified the embedded node Ready plus public HTTPS HTTP 200.
- **CouchLoom network audit:** retained its `homelab-net` membership because
  `vaults.json` resolves the Pi5 CouchDB service as `couchdb:5984`. This remains
  an intentional data-client exception until a dedicated CouchDB network path
  is introduced and verified.
- **GitLab network cleanup:** created `gitlab-net`, attached Redis, moved GitLab
  to `edge-http-net + gitlab-net + pg-net`, and moved all three GitLab tunnel
  clients to `gitlab-net` only. The Redis Compose override was validated and
  GitLab public HTTPS returned HTTP 200 after its controlled Omnibus restart.
- **Pi5 Compose drift reconciliation:** updated the source Compose declarations
  for the live RustFS and CouchDB edge/data networks, validated the full Compose
  config, and did not recreate any service. Backup:
  `/ssd-data/infra/docker-compose.yml.bak-compose-reconcile-20261020-155327`.

- Added `automation/maintenance/systemd/journald.conf.d/60-homelab-retention.conf`
  for a `1G` persistent journal budget, `20G` free-space floor, `128M` journal
  file cap and `14-day` retention. Docker and application containers are not
  restarted by this change. After rotation/vacuum, VM100 journald measured
  `992.2M` and `/` measured `50G` free (`75%` used), compared with `3.3G` and
  `48G` before the change. The 32 running container IDs were unchanged. B6
  remains open for Docker per-container log policy, threshold tests and
  retired-image review; VM100 is a Swarm worker, so service-level logging
  policy must be audited from the manager before any update.
- Added a manager-side read-only Swarm logging audit. It inventories only
  service name, image and log bounds, and makes no service mutation.
- **PostgreSQL network isolation (2026-10-20):** removed the live `postgres`
  endpoint from `homelab-net` after confirming all database consumers on
  `pg-net`; terminated one idle legacy PgBouncer backend session, which
  reconnected through `10.0.30.4`. Postgres stayed healthy and RelayHub,
  GitLab, Whiteboard and n8n returned HTTP 200. Compose backup remains on Pi5.
- **NetBird PgBouncer migration (2026-10-20):** moved
  `netbird_netbird-server` from `homelab-net` to `pg-net` while preserving
  `netbird-net` and `edge-http-net`. The task converged, used its existing
  PgBouncer DSNs, root domain stayed HTTP 200, and six legacy `172.30.0.91`
  client sockets were removed.
- **macOCR private-network migration (2026-10-20):** moved macOCR from
  `homelab-net` to `pg-net` plus `macocr-redis-net`, persisted the Redis
  override, and verified OCR `/healthz` and `/docs/` returned 200. Its old
  PgBouncer sockets on `172.30.0.92` are gone.
- **RelayHub database network migration (2026-10-20):** moved API and worker
  from `10.10.0.5:5432` to `pgbouncer:6432` on `pg-net`; API also uses
  `edge-http-net`. Both containers are healthy, public `/readyz` is 200, and
  PostgreSQL shows RelayHub through PgBouncer at `10.0.30.4`.
- **PgBouncer LAN bind hardening (2026-10-20):** narrowed the host listener
  from `0.0.0.0:5432` to `10.10.0.5:5432`. PgBouncer was recreated after
  clearing stale container metadata; Postgres was not restarted, all checked
  routes returned 200, and RelayHub worker recovered healthy.

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
- **Backlog (2026-10-20):** all open items moved to [BACKLOG.md](./BACKLOG.md), including the backup assessment (health failed 2026-10-18/19, restore drill and second target still open).
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
  with the local development config; DeepSeek-V4.1-Flash is now configured in
  production. Values
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
## 2026-10-20 — Network hardening N4 completed

- Bound Pi5 PgBouncer `5432`, Redis `16379`, VictoriaMetrics `8428`, and
  Alertmanager `9093` to `10.10.0.5` instead of all interfaces.
- Recreated only VictoriaMetrics and Alertmanager; persistent volumes and
  configuration were preserved. LAN health probes returned 200, and the
  RelayHub, GitLab, Whiteboard, n8n, OCR and MyPocket API-only route checks
  remained consistent with their documented behavior (`money` root is
  intentionally 404 while MyPocket web is stopped).
- Backups retained on Pi5:
  `/ssd-data/infra/docker-compose.yml.bak-bind-victoriametrics-20261020-215518`
  and `/ssd-data/infra/docker-compose.yml.bak-bind-alertmanager-20261020-215607`.

## 2026-10-20 — Network hardening N5 first app migration

- Attached Pi5 `redis-prod` to the existing `mypocket-redis-net` with the
  stable `redis-prod` alias and persisted that membership in the Redis Compose
  override.
- Removed `homelab-net` from MyPocket API and worker one service at a time.
  The API needed `edge-http-net` added explicitly after the first probe exposed
  the old implicit ingress dependency; the task recovered healthy and the
  public API health/docs probes returned 200/302.
- The first attempted API update rolled back safely because the Redis overlay
  endpoint was missing; the failed task was inspected and the service returned
  to its prior healthy state before retrying.

## 2026-10-20 — Network hardening N5 HTTP app migrations

- NetBird dashboard moved from `homelab-net` to `netbird-net` plus
  `edge-http-net`. The active Traefik route was corrected from the stale
  `tasks.netbird-dashboard` name to `tasks.netbird_netbird-dashboard`; public
  `netbird.dungxbuif.com` returned 200 after reload.
- K8s Syntax moved to `edge-http-net`; root returned 200 and `src/app.mjs`
  retained `application/javascript` content type.
- OpenClaw moved to `edge-http-net`; its persisted
  `gateway.trustedProxies` now includes only the edge overlay
  `10.0.1.0/24` in addition to the existing trusted peers. The service became
  healthy and the public Control UI returned 200. State backup:
  `/opt/apps/openclaw/state/openclaw.json.bak-edge-net-20261020-150621`.

## 2026-10-20 — Backup health B5 lock-aware check

- Added class-specific runtime limits and lock-owner-aware reporting to
  `backup/scripts/check-backup-health.sh`. A valid in-progress backup no longer
  appears as a failed health run; a stale or overlong unit, or a lock without a
  matching unit, remains a failure.
- Fixed the shared-lock open path for hosts using `fs.protected_regular`: the
  health process creates the lock only when absent and opens it read-only before
  calling `flock`.
- Deployed the identical script to VM100 and Pi5. The VM100 systemd health
  service returned exit `0`; the restricted Pi health command returned success.
  Script SHA-256: `837f566d6d55e78ddf4280f5cd5f506a98b1e551daaa8931cdd2c2d46bd875b5`.
- Focused health tests (8), scheduler contract tests, and `git diff --check`
  passed. The remaining B5 work is schedule/cadence separation, not the
  lock-aware health behavior.

## 2026-10-20 — Route catalog source repair E2/E3

- Repaired the two NetBird backend entries that had been dedented outside
  their `backend` maps. The catalog now parses and renders 26 routers and 25
  shared backend services with the current Swarm service names; the live
  Whiteboard route is also declared.
- Regenerated `automation/routes/generated/pi5-traefik.yml`. All 13 route
  contract tests pass; the artifact was subsequently published and smoke-tested
  in the following entry.

## 2026-10-20 — Backup schedule separation B5

- Deployed the new local schedule to VM100: RustFS at 02:00, GitLab at 02:30,
  retention at 06:30, and health at 08:00. Database and instance backups remain
  at 01:00 and 01:30. Timer reload/restart caused one `Persistent=true`
  catch-up retention run immediately; it is running under the existing lock and
  is being observed to terminal completion.
- Source schedule and timer contract tests pass. This closes the schedule
  deployment portion of B5; three consecutive clean nights remain for final
  acceptance.

## 2026-10-20 — Configuration backup inventory B2

- Added `backup/configs-sources.json` with explicit live Pi5 and VM100 sources,
  required/optional classification, and exclusions for runtime data and old
  stacks.
- Added the standalone fail-closed validator
  `backup/scripts/validate-config-sources.py`. Three local tests pass; live
  read-only validation found all six required Pi5 sources and all five required
  VM100 sources. The configs timer remains disabled until collection, retention,
  and scratch-restore integration are complete.

## 2026-10-20 — Route catalog publish E2/E3

- Published the validated generated catalog atomically to Pi5 Traefik after
  preserving a timestamped rollback copy. The catalog now owns the live
  Whiteboard route, the CouchDB/Sync-DB split, and explicit shared NetBird
  service names.
- Route contract tests passed. Whiteboard, KubeKosh, NetBird, and OpenClaw
  returned 200; Sync-DB returned the expected 401 at `/` and 404 for the
  disallowed `/_utils/` path. No Traefik configuration errors appeared in the
  reload window.

## 2026-10-20 — Configuration backup class integration B2

- Added the `configs` Restic repository mapping at
  `homelab-backups/configs`, plus a 14/8/12 retention policy and restore
  admission.
- Added VM100-only config retention and bounded local cleanup. It is skipped
  until the first successful config marker, so the existing retention job is
  unchanged while the class is disabled.
- Added a disabled 09:00 schedule declaration. No timer was enabled and no
  upload was started in this step.
- Config tests (5), scheduler contract, runner contract, shell syntax, and
  inventory validation passed. Manual upload and scratch restore remain the
  next gates.

## 2026-10-20 — Configuration backup safety gates B2

- Closed the pre-enable audit findings: VM100 Ansible staging now includes the
  collector, validator, config retention, and inventory; the Pi health repair
  playbook includes the exporter; the temporary Pi archive uses `mktemp` under
  `umask 077`; and the collector verifies every required Pi path after archive
  extraction.
- Added `configs` runtime limits to health reporting and installed the
  disabled configs timer with the same `Asia/Ho_Chi_Minh` calendar format as
  the existing timers.
- Deployed the corrected runtime files to VM100/Pi5. The disabled timer is
  confirmed `disabled`/`inactive`; no restart or production service mutation
  was performed.
- Scratch collection remains verified; the first encrypted upload is waiting
  for the existing long-running retention check to release the global lock.

## 2026-10-20 — Scheduled backup lock wait

- VM100 scheduled backup classes now wait up to one hour for the shared backup
  lock and retry every 30 seconds instead of failing immediately when a long
  retention check is in progress. Direct Pi executor calls remain non-blocking.
- The runner contract, shell syntax, config tests, and Ansible deployment
  contract passed; the updated scheduler and runner were deployed to VM100
  without restarting the active retention job.

## 2026-10-20 — Configuration repository preflight B2

- Started the first real `configs` service with the bounded lock wait. It
  collected a complete atomic run, then stopped at Restic preflight because
  the dedicated `homelab-backups/configs` repository does not exist.
- This is an expected fail-closed result: the uploader refused implicit
  repository initialization and no config data was uploaded. After the active
  retention lock releases, initialize the repository explicitly, rerun the
  class, verify the snapshot, and perform the scratch restore before enabling
  the timer.

### 2026-10-21 - Backup retention catch-up and remote-runner guard

- The latest VM100 health run passed for the existing database, instance, and RustFS classes; the first `configs` run correctly failed closed because its dedicated Restic repository was not initialized.
- A catch-up retention run remains active on Pi5 and is currently in a Restic integrity check. It is being preserved until terminal rather than interrupted.
- Added a bounded 4-hour timeout to VM100-to-Pi5 backup SSH commands and taught Pi health to recognize an active forced-SSH backup process while its lock is held. Unit tests and scheduler contract tests pass.
- The timeout/health change is staged in the workspace but publication is gated until the active retention unit becomes idle.
- The first configs repository bootstrap exposed a second runtime issue: the
  Restic container did not have an explicit writable cache location. The
  wrapper now sets `HOME=/tmp` and `RESTIC_CACHE_DIR=/tmp/restic-cache`; a
  local repository snapshot probe passes with this configuration.
- The first configs upload completed with 44 new files and a successful
  integrity check. Read-only snapshot metadata and restore operations now use
  `--no-lock` after the verified upload/check, preventing stale lock objects
  from blocking post-check or scratch restore indefinitely.
- The configs acceptance run completed as snapshot
  `d4ea082a8334cd8baab64c7afa1daf37d98a1eca7661e6b149eefc54030a7025`.
  Restic reported no errors; a local rclone mirror restored 44 files / 361 MiB
  and `sha256sum -c` passed. The scratch copy is removed after verification;
  the configs timer is ready to enable.
- During the first post-acceptance health run, a live Pi5 database job exposed
  a regex gap in remote-process detection (`run-class.sh` was not matched) and
  a missing-marker warning during an active run. The pattern and marker logic
  were corrected so active classes report `deferred_active` until their marker
  is written.

### 2026-10-21 - Bound nightly Restic verification

- Changed upload and retention verification to run structure-only `restic check` by default.
- A deep payload read is now explicit via `RESTIC_READ_DATA_SUBSET=1/10`, reserving Google Drive pack reads for the weekly integrity window.
- Added contract coverage and updated the backup runner documentation and B5 backlog status.
- Added the Sunday `homelab-backup-verify-weekly` service/timer. It performs the explicit 10% payload check across Pi5 and VM100 repositories under the same lock, without pruning.
- Spaced the production schedule to 01:00 databases, 03:00 instances, 04:00 RustFS, 05:00 GitLab, 10:00 retention, 12:00 health and 13:00 configs after a RustFS lock collision at the former 02:00 slot.
- Ran the bounded local staging cleanup on VM100 and Pi5. It removed one old completed `database-instances` run and one old completed `databases` run; two completed runs and all incomplete/active runs were preserved. VM100 had 33G free while GitLab catch-up was writing; Pi5 had 278G free.
- Restore drill passed for `database-instances` snapshot `9bb08b02efe6c5fc1e7163cd7de74927c8e3017e25b8df2f91b2fb63e032d347`: 7 restored files, all checksum entries passed, scratch target removed. B1 remains open for PostgreSQL/CouchDB, RustFS and GitLab coverage.
- Added health disk thresholds: 85% usage warns and 92% fails, while retaining the 10 GiB minimum-free-space gate.
- Recovered the interrupted `databases-20261020-180001` run after the old uploader parse failure. Reused its completed export, reran the new deduplicated upload/structural check, wrote marker success, and received snapshot `45fc58a1c463cb5ec85a008007e26ee1f0e5376d40ee1f858d2afe50436762cb`. Live health now exits 0 with only the expected 86% disk warning while GitLab is active.
- **GitLab backup follow-up:** native export `gitlab-20261020-190208` completed with an 8.74 GB archive and Restic upload; the mandatory structural check was still active at 20:02 UTC, so the success marker and cleanup were not assumed. VM100 was 87% used with about 26 GB free. Tagged rollback images and a stopped family-tree reference were observed; no image was removed while the backup was active.
- **Backup upload latency fix prepared:** Drive index enumeration made preflight and inline structural checking hold backup locks for minutes. `upload-restic.sh` now defaults to `cat config` preflight and takes the snapshot ID from the backup summary; structural checking remains in retention/deep-verify, with explicit opt-ins for snapshot preflight and inline check. Upload immutability, default-deferred behavior, stale-lock and Restic contract tests pass locally. Deployment waits for the active database-instances check to finish.
- **Backup transport acceptance 2026-10-21:** controlled `database-instances-20261020-202507` completed with snapshot `164f85eb25e03f936a9cba0c29185d00712bf4cfbc155d1818726224ea3e72c7`. The Drive pacer default is now `100ms` with burst `1`; the prior `10s` default was the observed lock/latency bottleneck. GitLab run `gitlab-20261020-190208` passed archive checksums 4/4 and remote snapshot verification (`a0cbb341f856d2ef324cb57b4ddb29dc4eab23f22c6909e9c0d131531cac26fb`); its success marker and Mezon success were restored. One old completed staging run was removed. VM100 ended at 83% used with 34GB free; health exited 0.
- **VM100 disk cleanup 2026-10-21:** read-only inventory found no Dead Swarm tasks. After checking that no container referenced the retired Educates image, removed the created `tmpfs-repro-repro-1` test container and `ghcr.io/educates/educates-base-environment:3.8.0` (5.28GB). Docker daemon remained healthy; VM100 ended at 81% used with 39GB free and 34 running containers.
- **Docker maintenance guard 2026-10-21:** `docker system df` was reproduced as a potentially hanging read when stale layer metadata is present. Added a 30-second timeout with a non-fatal warning, deployed the maintenance script to VM100, and ran the service successfully: no Dead tasks, running containers unchanged, and the accounting report completed. The timer no longer turns a reporting failure into a cleanup failure.
- **AI model audit 2026-10-21:** VM100 runtime inspection found OpenClaw, Whiteboard and MyPocket API already on `DeepSeek-V4.1-Flash`; `mypocket-worker` still used `qwen/qwen3.6-35b-a3b`. OmniScan's production template and documentation were updated to `DeepSeek-V4.1-Flash`. The worker update is intentionally pending until Pi5 manager SSH recovers; VM100 cannot mutate Swarm service specs.
- **AI model audit automation 2026-10-21:** added the secret-free read-only checker `automation/scripts/audit-ai-models.sh`, contract-tested it, and installed it on VM100. Live result: OpenClaw, both Whiteboard selectors, and MyPocket API pass; only MyPocket worker fails with the old Qwen selector. The checker is now the verification gate for the pending manager-side update.
- **Manager transport verification 2026-10-21:** Semaphore task `#139` reached the Pi5 approval assertion but failed as `UNREACHABLE` on the first remote install task. This confirms the pending model update is blocked by Pi5 transport/SSH, not by the Ansible playbook or model value; no repeated retry job was left active.
- **AI source-config reconciliation 2026-10-21:** aligned `OMNISCAN_SECRETS.LLM_MODEL` and `MYPOCKET_SECRETS.AI_MODEL` in `local_vars.json` to `DeepSeek-V4.1-Flash`. JSON validation passed and no endpoint or credential field was changed. Runtime verification still reports only the Swarm `mypocket-worker` as stale.
- **Backup test verification 2026-10-21:** ran the complete `backup/tests` suite in a Linux container with `flock` and the required Python dependencies: 116 tests passed, 1 intentionally skipped. The same suite on macOS reports only the expected environment error because macOS does not ship the Linux `flock` command; production backup execution remains Linux-based and was verified in the Linux run.
- **Backup control-plane reconciliation 2026-10-21:** health now checks `homelab-backup@configs.service`; the Ansible backup audit includes the configs marker, unit outcome and journal evidence; and the runtime deployment playbook installs and enables the configs and weekly verification timer units while refusing publication during an active configs/deep-verify job. Linux verification now passes `117` backup tests and `29` Ansible tests. This is prepared in the repo; production publication still requires the existing controlled VM100 deployment window.
- **NetBird documentation reconciliation 2026-10-21:** corrected the remaining active docs that named retired `tasks.netbird-server`/`tasks.netbird-dashboard` DNS records. They now match the live Swarm service names `tasks.netbird_netbird-server` and `tasks.netbird_netbird-dashboard`; archived topology notes remain historical by design.
- **Repository publication 2026-10-21:** committed the verified automation/backup/doc reconciliation as `f412452` and pushed it to GitLab branch `codex/relayhub-source-foundation`. The local `gitlab` remote now uses HTTPS because LAN DNS resolves the SSH hostname to Pi5, where port `2222` is intentionally not published; future pushes must use the protected GitLab credential helper, never a credential embedded in the URL.
- **VM100 maintenance recheck 2026-10-21:** direct read-only runtime audit found 34 running containers, no `dead` or `created` containers, 42 GB free before maintenance, and only four dangling volumes that remain intentionally retained for PostgreSQL, registry `workshop-files`, and MyPocket backup data. `homelab-docker-maintenance.service` then exited 0. BuildKit reported 7.4 GB reclaimable but its cache entries are still referenced/recent, so no unsafe cache deletion was performed.
- **VM100 build-cache recheck 2026-10-21:** ran the same seven-day `docker builder prune` policy outside the backup window. It reclaimed `0B`; Docker still reports 7.437 GiB logical reclaimable cache and 30 GiB free / 85% used. No image, container, volume or service changed.
- **Pi5 backup resource cap 2026-10-21:** Semaphore task `#144` released the bounded `run-pi-capped.sh` launcher plus the restricted executor and SSH guard to Pi5 from commit `8e35a85`. The release completed with `unreachable=0` and `failed=0`; portable `nice/ionice` mode is active by default. Systemd cgroup mode remains a separately gated follow-up.
- **Legacy Pi backup retirement 2026-10-21:** verified `/ssd-data/backup/simple-backup.sh` had only a commented cron entry, no running process, and was superseded by the current systemd backup timers. Removed the obsolete script after B1 restore acceptance; no active backup schedule or data volume was touched.
- **Break-glass procedure 2026-10-21:** documented the operator-only workstation recovery path for 1Password SSH signing, pinned host-key checks, bounded read-only validation, mutation evidence and return to GitLab/Semaphore. No credential or SSH policy was changed; A4 is complete as a documentation gate.
- **Restore acceptance 2026-10-21:** restored `database-instances-20261020-202507` snapshot `164f85...e72c7` into an isolated VM100 `pgvector/pgvector:0.8.6-pg17-bookworm` container. `pg_restore` succeeded, `SELECT 1` passed, 226 relations and vector extension 0.8.6 were verified; scratch container, network and 27 MiB dump directory were removed. B1 is still partial and B8 is not yet automated.
- **VM100 resource audit 2026-10-21:** read-only sample found GitLab 2.45 GiB under its 10 GiB/4 CPU cap, KubeKosh 967 MiB under 4 GiB/2 CPU, Stirling 288 MiB under 2 GiB/2 CPU, and no current memory pressure. OpenClaw, n8n, MyPocket, OCR, RelayHub, NetBird and CouchLoom PostgreSQL have no Docker cap; measured workload canaries are required before manager-side limits are applied.
- **Nightly drift preflight 2026-10-21:** reran the drift/evidence/network/collector/private-artifact tests in the pinned automation venv; all 19 tests passed. A live read-only VM100 probe confirmed it is a Swarm worker (`ControlAvailable=false`), so `docker service ls` is correctly rejected there. A2 remains fail-closed and open: manager-side service evidence and the final scheduled Mezon report must come from the Pi5 manager after its restricted SSH transport is restored.
- **GitLab restore acceptance 2026-10-21:** verified the latest `gitlab-20261020-190208` snapshot (`a0cbb341...cac26fb`) with archive SHA-256, 105 tar entries, registry/database gzip checks, and a native SQL restore into an isolated PostgreSQL 17/pgvector scratch container. `SELECT 1` passed; 928 public relations, 3 users, 5 projects and the required PostgreSQL extensions were present. Scratch resources and logs were removed. B1 remains partial for the shared PostgreSQL/CouchDB class and RustFS; this evidence does not claim a full disposable GitLab application boot.
- **Shared database restore acceptance 2026-10-21:** restored the latest `databases-20261020-180001` snapshot (`45fc58a1...762cb`) to VM100 scratch: 38 files/directories and 6.456 GiB completed in 7:29, all checksum entries passed, native PostgreSQL `bds_prod` restore/`SELECT 1` passed, and native CouchDB `obsidian_vault` restore matched 49,210 documents. Retired `goclaw`/`omniscan` were absent. Scratch containers, payload, logs and CouchDB image were removed; disk returned to 81% used. B1 now has RustFS as the remaining restore class, while B8 monthly automation remains open.
- **RustFS restore acceptance 2026-10-21:** restored latest snapshot `667cb322...942c` (718.848 MiB, 3,114 checksummed entries) into an internal RustFS 1.0.0-rc.1 scratch instance. `mac-ocr` was copied to an isolated bucket and the deployed helper verified 62 objects/key-size entries. This exposed and fixed a deployed-layout import bug in `restore-bucket.py`; source test passed, helper was deployed with rollback copy, and all scratch resources/images/payload were removed. B1 is complete; B8 monthly unattended restore remains open.
- **MyPocket worker model rollout 2026-10-21:** used the approved Pi5 manager release identity to update only `mypocket-worker`'s `AI_MODEL` with start-first ordering. Docker reported `update completed`; the replacement task is running with `DeepSeek-V4.1-Flash`. VM100's model audit passed all five selectors and Money `/api/v1/health` returned HTTP 200.
- **Monitoring target cleanup 2026-10-21:** removed the retired Kubernetes, Pi5 node-exporter and VPS node-exporter scrape jobs from Pi5's live VictoriaMetrics config, kept a timestamped rollback copy, validated Compose, and restarted only VictoriaMetrics. The ready probe passed and `/api/v1/targets` now has 14 active targets; old `up=0` history remains by design.
- **VM100 retention ownership 2026-10-21:** deployed commit `6a51922` to move Pi5 `databases`/`rustfs` retention and weekly integrity checks to VM100. Pi5 now exports success markers through the restricted `markers` command; live VM100-to-Pi5 marker transport passed for the latest successful snapshots. Found and repaired a compatibility gap where the authorized key invoked historical `homelab-backup-ssh-guard`/`homelab-backup-executor` aliases; both release playbooks now publish current and historical names. The first scheduled destructive retention run remains the acceptance gate; no manual prune was run.
- **VM100 retention acceptance 2026-10-21:** reran `databases` successfully with snapshot `8f1d38f7...7a670`, then VM100 retention passed integrity/prune for `databases`, `rustfs`, and GitLab. A stale `database-instances` lock from an interrupted run was removed only after no Restic/rclone process was present; the dedicated instance retention wrapper then passed and cleaned five old local staging runs. Added stale-lock retry logic to `verify-retention.sh`, deployed it with rollback copy, reset only the already-resolved systemd failure state, and reran health successfully: VM100 82% used, 36.2 GB free, lock free; Pi5 health passed.
- **VM100 local staging policy 2026-10-21:** after GitLab restore acceptance, changed the VM100 scheduler to keep one complete GitLab staging run instead of two. Removed only the older verified `gitlab-20261020-190208` local run (about 8.2 GiB); incomplete runs were preserved. VM100 now reports about 37 GB free / 82% used. Scheduler contract passed and the updated runner was published with a rollback copy.
- **VM100 rollback image review 2026-10-21:** manager-side Swarm service evidence showed the two Whiteboard rollback tags were unused; removed only `homelab/whiteboard-backend:rollback-20261019-v1` and `homelab/whiteboard-frontend:rollback-20261019-v1`. Docker stayed healthy, 33 active images/34 running containers were unchanged, and VM100 remained at 82% used with 36 GB free. BuildKit cache was not pruned because its 7.437 GiB logical reclaimable set remains recent/referenced.
- **CouchDB follow-up audit 2026-10-21:** read-only Pi5 check found the `couchdb:3.3.3` container at 0.40% CPU and 123.3 MiB RSS, no active tasks, 14 `_changes` log mentions, 12 HTTP 401s, 3 HTTP 404s and no 5xx in the bounded 24-hour scan. No rate limit or LiveSync change was made; B11 is closed with passive monitoring.
- **Pi5 container-history cleanup 2026-10-21:** manager-side review found 11 stopped RelayHub Compose, Semaphore and provisioner task containers and no dead containers. Removed only those stopped container IDs; preserved all named data volumes and left 20 running Pi5 containers unchanged. Pi5 disk remained healthy at 40% used with 271 GB free.
- **Pi5 BuildKit cleanup 2026-10-21:** verified no active build process, then ran the approved 168-hour builder prune. Docker reclaimed 13.5 GiB of inactive cache; Pi5 moved from 40% to 37% used with 284 GB free. Remaining 25.55 GiB is inactive cache; data volumes, images and running services were unchanged.
- **Scheduled monitoring drift report 2026-10-21:** added a VM100 systemd timer at 11:30 Asia/Ho_Chi_Minh that runs the existing read-only VictoriaMetrics active-target audit and sends a compact result via the existing Mezon notifier. The first release failed closed because the wrapper dependency was missing from the VM100 app tree; the dependency was added to the release contract, redeployed with a rollback copy, and the service then completed with `Result=success` and `ExecMainStatus=0`. The timer is enabled and active. A2 is now partial: scheduled target reporting is complete; manager-side Docker service inventory drift still needs a Pi5 manager execution path.
- **VM100 disk policy review 2026-10-21:** closed B6 after reconciling the deployed maintenance script with live evidence. Image and BuildKit cleanup are age-bounded at seven days, BuildKit retains 5GB, volumes are never pruned, and the recheck reclaimed `0B` because the remaining cache was recent or referenced. Disk pressure remains an observation item, not authorization for a broad prune.
- **B9 backup pull network preflight 2026-10-21:** from disposable probes on VM100, `pgbouncer:6432` on `pg-net`, `rustfs:9000` on `s3-net`, and `couchdb:5984` on `homelab-net` all accepted TCP connections through Docker service DNS. No export, credential, restart, or public port changed; this clears the network gate for the one-week native-export comparison before Pi5 export retirement.
- **B9 PgBouncer auth audit 2026-10-21:** PgBouncer uses `scram-sha-256` with `auth_file`; its existing auth path is for application traffic only. Native backup was deliberately moved to direct `postgres-pg:5432` on `pg-net`, avoiding a PgBouncer auth-file dependency.
- **B9 native PostgreSQL identity 2026-10-21:** created the least-privilege `backup_ro` role on Pi5 (`NOSUPERUSER`, `NOCREATEDB`, `NOCREATEROLE`, `NOREPLICATION`) and enrolled its root-owned `640` credential file on VM100. Verified login and a custom-format `pg_dump` over private `pg-net` to `postgres-pg:5432`; PgBouncer is intentionally excluded from this backup path. The globals adapter now passes `--no-role-passwords`.
- **B9 native PostgreSQL live probe 2026-10-21:** VM100 disposable `postgres:17-alpine` client authenticated as `backup_ro` over `pg-net`, produced a non-empty `relayhub` custom archive, and passed `pg_restore --list`. The scheduler remains on the Pi export path until the source adapter is deployed and the one-week comparison window is started.
- **B9 combined comparison gate 2026-10-21:** deployed the native PostgreSQL adapter and ran the full database runner. PostgreSQL globals and custom-format dumps passed; the run stopped at CouchDB because VM100 has no CouchDB container or read-only credential. Rolled back the native PostgreSQL runtime variables so the scheduled combined class remains on the known-good Pi5 path. No backup window was left degraded.
- **B9 CouchDB ACL audit 2026-10-21:** CouchDB has no permission-enforced read-only member role, and `_users` security rejected direct member enrollment with `403`; the attempted temporary user and ACL changes were rolled back. The next design is a Pi5-local GET-only proxy with a separate VM100 token. No CouchDB credential was left on VM100 and no production ACL drift remains.
- **Backup runtime audit 2026-10-21:** VM100 database, instance, RustFS, GitLab and health timers are active with no failed units; VM100 root filesystem is 82% used with about 37 GB free. Pi5 Postgres, PgBouncer, CouchDB, RustFS and edge containers are running. Native backup runtime remains disabled pending the CouchDB proxy decision.
- **External heartbeat 2026-10-21:** deployed the transition-only public-route heartbeat on the VPS. The five-minute systemd timer and one-shot service are healthy; homepage, RelayHub, and OCR public probes all returned HTTP 200. The Mezon webhook was transferred from the existing VM100 secret without printing it and is stored on VPS mode `0600`; no routing, container, or port changed.
- **Manager-side Swarm inventory 2026-10-21:** released the reviewed `swarm_services` probe to the Pi5 host observer with a timestamped rollback copy. The direct helper check reported `manager=true`; Semaphore task `#149` then completed read-only with `ok=4`, `failed=0`, `unreachable=0` and 25 live Swarm services. A2 is complete; the daily VM100 target-drift timer remains active for continued observation.
- **VM100 resource baseline 2026-10-21:** Semaphore task `#150` completed read-only with `ok=4`, `failed=0`, `unreachable=0`. Existing limits were confirmed for GitLab, KubeKosh, Stirling, the Semaphore runner, CouchLoom, tunnels, K8s Syntax and the pg-net anchor; OpenClaw, n8n, MyPocket, OCR, RelayHub and NetBird remain uncapped. No limits or services were changed; A6 now requires one-service-at-a-time canaries.
- **Monitoring drift rollout hardening 2026-10-21:** two transient notifications showed the old repair order could run the timer after the wrapper copy but before its audit dependency. The playbook now installs the dependency first, verifies both executable files before enabling the timer, and has a contract test covering the order. The live VM100 unit currently has both files and the latest one-shot passed.
- **Homepage resource canary 2026-10-21:** applied `0.50 CPU` and `512 MiB` to the one-replica Homepage Swarm service with `start-first`, rollback-on-failure and the existing approved image digest. Swarm reported `update completed`; the new task is running and `https://dungxbuif.com/` returned HTTP 200. The catalog and VM100 docs now record the applied limit.
- **macOCR resource canary 2026-10-21:** applied `1 CPU` and `1 GiB` to `macocr-proxy` with stop-first and rollback-on-failure. Swarm reported `update completed`; the image stayed unchanged and OCR `/healthz`, `/readyz` and OpenAPI probes returned HTTP 200. The catalog and VM100 docs now record the applied limit.
- **n8n resource canary 2026-10-21:** applied `1 CPU` and `2 GiB` to `n8n` with stop-first and rollback-on-failure. The replacement task needed its normal warm-up, then became Docker-health `healthy`; Swarm reported `update completed` and both `/healthz` and `/` returned HTTP 200. Existing deprecation/PostgreSQL compatibility warnings remain unrelated follow-up items.
