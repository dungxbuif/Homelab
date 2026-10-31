---
type: Reference
title: "Homelab Backlog"
description: "Consolidated open work from the 2026-10-19/21 audit and network-hardening rollout, ordered by priority"
timestamp: 2026-10-31T10:30:00+07:00
---

# Homelab Backlog

Sources: [network, workload and automation audit](./research/network-workload-automation-audit-2026-10-19.md),
[network hardening rollout](./deployments/network-hardening-2026-10-19.md),
[backup runbook](./runbooks/backup-restore.md), and the 2026-10-21 operating session.
Status values: `open`, `ready` (script prepared, not run), `blocked`, `decision`.

## Reconciliation — 2026-10-31

- **R3 / CloudBeaver:** confirmed complete on 2026-10-28: the clean persistent
  workspace, operator login, private PostgreSQL connection and database explorer
  were verified.
- **R4 / Databasus:** the operational backup gate is now evidenced: admin access,
  Google Drive storage, 15 PostgreSQL jobs, successful artifacts and the Mezon
  test notification were verified on 2026-10-28. On 2026-10-31 the Pi5 agent
  passed post-upgrade backup + restore checks for all six approved service DBs;
  non-service jobs remain a separate scope decision.
- **R6 / documentation:** active indexes, status references and the external OKF
  v0.2 reference were reconciled on 2026-10-29; broader documentation
  organization remains open.
- **Two-agent backlog double-check:** read-only agents revalidated the backlog
  against the live Pi5/VM100 state and dated evidence. U2/U3/U4/U6 and B13
  are now `done`; U1/U5/U7/U9 remain `partial`; B2/B4/B5/B8 were reopened
  because their VM100 timers are currently disabled/inactive. All other rows
  retain their prior status unless their acceptance evidence changed.
- **Project inventory reconciliation:** `/home/dungxbuif/workspace/projects/`
  now has 46 real project directories and `PROJECTS.md` matches them exactly;
  deleted/stale rows were removed, and the dangling Mac-path compatibility
  symlink is excluded from the current-project table.
- **GitLab mirror requirement:** the next R7 wave must use the GitLab token to
  create/verify a corresponding project and add a second GitLab remote for
  every approved Git repository. The read-only remote audit found 35 Git repos,
  4 already using GitLab as an origin, 31 without a GitLab remote (2 without
  any origin), and 11 non-Git directories. No project creation or source push
  has been performed; visibility and the non-Git scope must be decided first.
- **GitLab API root cause and repair:** the 2026-10-31 HTTP 500 was caused by
  Redis losing its overlay attachment during a base-only Compose recreate;
  GitLab's current `gitlab-net` path was restored and authenticated Redis DB2
  returned `PONG`. Evidence: [GitLab Redis network repair](./deployments/gitlab-redis-network-repair-2026-10-31.md).

## Requested work — 2026-10-28

These items were added from the latest operating request. They are intentionally
backlog entries; production changes require a separate verification pass.

| ID | Item | Scope / acceptance gate | Status |
|---|---|---|---|
| R1 | Audit and normalize all Pi databases | Inventory PostgreSQL, CouchDB, Redis, RustFS metadata and service-owned stores; document owner, host, backup class and retention. | open |
| R2 | Move stray databases to Pi5 | Identify DBs outside the Pi5 data boundary, migrate one engine at a time, and pass application/read-only restore checks before cleanup. | partial (2026-10-28; legacy Pi5 RelayHub PostgreSQL was empty, production already used common Pi5 PostgreSQL, archived, validated, and removed after approval) |
| R3 | CloudBeaver as the DB coordination UI | Configure CloudBeaver with least-privilege app connections, no public database exposure, and one smoke query per registered connection. | done |
| R4 | Verify Databasus-to-Drive backups | Check every configured provider, recent artifacts, checksum/restore evidence, retention and alert path; close only after a real restore. | partial (2026-10-31; all six approved service DBs passed provider backup + automatic restore; other Databasus jobs await scope decision) |
| R5 | Clean VM100 state | Inventory persistent volumes, runtime state and rollback artifacts; move state to the approved data/backup host, then remove only verified orphans. | open |
| R6 | Homelab documentation organization | Reconcile `INDEX`, `PROJECTS`, `STACK`, `STATUS`, runbooks and dated deployment evidence after the workspace split; keep project docs, exclude source checkouts. | partial (2026-10-31; current project inventory now reconciled; broader organization remains open) |
| R7 | Dual publication for project code | For each approved Git repository, create/verify one GitLab mirror using the password-manager token, add it as a second remote, push a dedicated branch first, and record the project URL/result. Existing GitLab-origin repos need verification rather than a duplicate project; non-Git directories and no-origin repos require explicit classification first. | blocked (2026-10-31 Redis/API repair complete; preflight PAT must be revoked/rotated after exposure before any external mutation) |
| R8 | SSH/API key migration | Inventory consumers, move keys to the approved password-manager boundary, rotate and revoke one key at a time, then verify each consumer. | open |
| R9 | Keep source code out of the homelab vault | Confirm project checkouts live under `/workspace/projects`, LiveSync is `docs/**` only, and no `node_modules`/build output is in the vault or DB. | in progress (project inventory reconciled; automated source/build-output guard remains) |
| R10 | GitLab/RustFS write-path review | Measure file growth and write frequency, classify durable data, and decide whether each workload can safely use a database without weakening restoreability. | open |
| R11 | Review every sync mechanism | Map Obsidian LiveSync, CouchLoom changes feed, backups and any remaining replication; verify source of truth, delete propagation, auth and rollback. | open |
| R12 | Fix n8n Mezon delivery path | Restored `daily-gold-fuel-mezon` from the verified pipeline backup. Its terminal node is `n8n-nodes-mezon.mezonWebhook` and the public endpoint host is `webhook.mezon.ai`; no bot node is in this workflow. | done (2026-10-28; Knowledge Hub bot workflows remain separate) |
| R13 | Rotate Homelab Mezon notifications into a Swarm secret | The requested Homelab channel webhook is now stored in 1Password as `Homelab Secret/Mezon - Homelab channel webhook`. The live `db-management_mezon_webhook` secret does not match it yet; replace it through the release path, verify sanitized delivery, then remove the old secret. | open |

## P0 Security

| ID | Item | Why | How / verify | Status |
|---|---|---|---|---|
| S1 | Public GitHub repo exposes credentials | Credentials in history are compromised regardless of repo state | Read-only audit on 2026-10-21 found no real credential in the public reachable refs; only deprecated placeholders matched. Issuer-side rotation is still required for anything previously exposed. Evidence: [GitHub credential exposure audit](./deployments/github-credential-exposure-audit-2026-10-21.md) | partial (audit pass; rotation required) |
| S2 | Root cause of the VPS HostSNI edit outage | Removing one hostname from `/root/gateway/dynamic.yml` took sites down for 3 to 4 minutes | Read-only forensic result classifies this as unsafe live file-provider mutation; generic guarded edit path is added and its 6-test contract suite passes. Exact historical watcher event remains unproven because no provider error was retained; live VPS dry-run/smoke still needs an approved hash and operator access. Evidence: [VPS HostSNI incident](./deployments/vps-hostsni-incident-2026-10-21.md) | partial (guard verified; historical reproduction and live dry-run pending) |

## P1 Network segmentation

| ID | Item | Why | How / verify | Status |
|---|---|---|---|---|
| N1 | Detach `homelab-net` from `postgres` | Shared flat network exposes Postgres to every service on it | Applied 2026-10-20: backed up compose, removed the source declaration, detached the endpoint, terminated one legacy PgBouncer backend session, verified all DB clients on `10.0.30.x`, Postgres healthy and four production routes 200. Backup: `/ssd-data/infra/docker-compose.yml.bak-pg-detach-20261020-214540` | done |
| N2 | Flush old pgbouncer server connections | App clients can retain PgBouncer connections on `homelab-net` during migration | Done 2026-10-20: NetBird and macOCR migrated to `pg-net`; legacy `172.30.0.91/.92` sockets are gone and DB sessions use `10.0.30.4` | done |
| N3 | relayhub reaches PgBouncer via LAN `10.10.0.5:5432` | Host port stays published only for this client | Done 2026-10-20: API and worker use `pgbouncer:6432` on `pg-net`; API also uses `edge-http-net`; both healthy and public `/readyz` 200 | done |
| N4 | Bind remaining host-published datastore ports | Datastores and monitoring APIs should not listen on all interfaces | Done 2026-10-20: PgBouncer `5432`, Redis `16379`, VictoriaMetrics `8428`, and Alertmanager `9093` bind only to `10.10.0.5`. Health/API probes passed and production route smoke checks remained healthy. | done |
| N5 | Keep `homelab-net` only where `redis-prod` is needed | The shared network is still a broad lateral-access boundary | Completed 2026-10-20. Production apps and GitLab tunnels were migrated one at a time. Documented exceptions are CouchLoom for Pi5 CouchDB DNS, plus Pi5 edge/data/control-plane services: Traefik, PgBouncer, RustFS, registry, Redis and provisioner. | done (documented exceptions) |
| N6 | Compose drift on Pi5 | Live RustFS/CouchDB endpoints had networks missing from the source Compose file | Done 2026-10-20: declared live RustFS and CouchDB edge/data networks; `docker compose config` passed; no service recreate. Backup: `/ssd-data/infra/docker-compose.yml.bak-compose-reconcile-20261020-155327` | done |

| A1 | Complete AI model rollout verification | Selector rollout is complete; quality must be checked without production data | `mypocket-worker` was updated on the Pi5 manager with `start-first`; Docker reported `update completed`, the new task is running, the model audit passes all five selectors, Money `/api/v1/health` returned 200, and the synthetic live MyPocket matrix passed all six cases after the `not_found` tool-drift fix (`23ecdca`). Owner-level business UAT remains separate. Evidence: [worker model release](./deployments/mypocket-worker-model-release-2026-10-21.md) and [AI rollout](./deployments/ai-model-rollout-2026-10-21.md). | partial (runtime and synthetic quality gates pass; owner UAT remains) |

## P1 Backup (see assessment below)

| ID | Item | Why | How / verify | Status |
|---|---|---|---|---|
| B1 | Remote Drive restore acceptance | Backups are unproven until a full restore works | Passed all four current backup classes: `database-instances` PostgreSQL 17/pgvector restore with 226 relations; GitLab native archive and SQL restore with 928 relations, 3 users and 5 projects; shared `databases` payload checksums plus native `bds_prod` and CouchDB `obsidian_vault` restores; RustFS payload checksums plus `mac-ocr` S3 restore with 62 objects. Evidence: [GitLab](./deployments/gitlab-restore-acceptance-2026-10-21.md), [databases](./deployments/databases-restore-acceptance-2026-10-21.md), [RustFS](./deployments/rustfs-restore-acceptance-2026-10-21.md). Full GitLab application boot remains an optional higher-cost drill; monthly unattended restore is B8. | done 2026-10-21 |
| B2 | Backup of host configs | Compose files, Traefik, Caddy, `/etc`, secrets are not a backup class | Historical encrypted `configs` snapshot/upload and scratch-restore checks passed, but the current `homelab-backup-configs.timer` audit is `disabled/inactive`; re-enable and verify the recurring schedule before closing. | open (reopened 2026-10-31; scheduler inactive) |
| B3 | VM100 vzdump | VM-level recovery has no image | Read-only Proxmox preflight 2026-10-21: VM100 is running with 6 vCPU/16 GiB/200 GiB; only `pre-docker-ce-20261014` exists; `local` has 89.8 GB free and `local-lvm` 100.0 GB free; no PBS/NAS storage is configured. Evidence: [vzdump preflight](./deployments/vm100-vzdump-preflight-2026-10-21.md). Add a separate failure-domain target before creating the first image backup. | open (target required) |
| B4 | Dead-man's switch and alerts | A silent scheduler failure goes unnoticed | Health/dead-man implementation and external heartbeat remain documented, but the current `homelab-backup-health.timer` audit is `disabled/inactive`; re-enable and observe a live scheduled run before closing. Evidence: [dead-man hardening](./deployments/backup-deadman-alerts-2026-10-21.md) and [external VPS heartbeat](./deployments/external-heartbeat-vps-2026-10-21.md). | open (reopened 2026-10-31; scheduler inactive) |
| B5 | Health check false negatives | 2026-10-19 health failed only because retention held the lock for 45 minutes | Lock-aware health code and prior recheck remain evidenced, but the current backup/weekly verification timers are disabled/inactive; re-enable the schedule and capture a fresh lock-free run before closing. | open (reopened 2026-10-31; scheduler inactive) |
| B6 | VM100 disk pressure | On 2026-10-18 only 105 MB was free: GitLab backup and retention failed | Maintenance policy is active; health warns at 85% and fails at 92%. The monthly restore payload, stale runtime candidates, old stopped containers and 11 anonymous Docker volumes were removed only after reference checks. GitLab restore acceptance is complete, so local GitLab staging now keeps one complete run; removing the older 8.2 GiB run reduced VM100 to about 36 GB free / 82% used. The named `mypocket-prod-backups` volume was retained. Unreferenced Whiteboard rollback tags were reviewed against manager service state and removed. Daily maintenance uses a seven-day age threshold, keeps 5GB of BuildKit cache, never prunes volumes, and a recheck reclaimed `0B` because remaining cache is recent or referenced. Evidence: [disk audit](./deployments/vm100-disk-audit-2026-10-21.md) and [orphan cleanup](./deployments/vm100-docker-orphan-cleanup-2026-10-21.md). No broad Docker prune is justified. | done 2026-10-21 (continue disk observation) |
| B7 | Second off-site target | Google Drive is the only remote copy | Keep one encrypted Google Drive copy with daily runs; a second target is deliberately out of scope for this lab | closed (2026-10-21 decision) |
| B8 | Monthly automated restore test | Replaces manual checks | Historical restore-drill acceptance exists, but the current `homelab-backup-restore-drill.timer` audit is `disabled/inactive`; re-enable and capture one fresh scheduled restore marker/notification before closing. Evidence: [acceptance](./deployments/backup-restore-drill-acceptance-2026-10-21.md) | open (reopened 2026-10-31; scheduler inactive) |
| B9 | Make Pi5 passive for backups | Pi5 runs export, restic upload, check and prune and holds restic and Drive secrets | VM100 now owns RustFS export/upload/retention: private `s3-net` endpoint, bucket-scoped read-only key, 7-bucket native export, 3,115 checksum entries, no missing key/size object against the latest Pi5 run, scratch restore of 62 `mac-ocr` objects, and an official systemd run passed with snapshot `d8a444b2ebad0046ad40c72c5e4145be10e830bbf48c3482cc62066323c94d92`. PostgreSQL native pull is verified. CouchDB's private GET-only proxy is deployed; `obsidian_vault` exported/restored with 49,210 documents. The experimental stream path now has a per-page free-space guard, durable metadata snapshot, remote post-check, and a manual two-snapshot restore orchestrator; the full `homelab` comparison was stopped at 83% VM100 disk usage and the scheduled `databases` class remains on Pi5. Source/contract coverage is included in the Linux backup suite (`136` pass, `1` skipped). Evidence: [native pull transport](./deployments/backup-native-pull-transport-2026-10-21.md), [RustFS cutover](./deployments/rustfs-native-pull-cutover-2026-10-21.md), [RustFS upgrade](./deployments/rustfs-upgrade-2026-10-21.md), [CouchDB proxy deployment](./deployments/couchdb-backup-proxy-2026-10-21.md), and [streaming research](./research/couchdb-restic-streaming-2026-10-21.md). | partial (RustFS/PostgreSQL done; CouchDB pending) |
| B10 | Cap any remaining Pi5 backup job | Protect the data server's latency | Root-owned class wrapper and argument-specific sudoers rules now enforce transient systemd scopes with `CPUQuota=100%`, `MemoryMax=1G`, and `IOWeight=50`; a real `configs` probe exited 0 with output suppressed. Portable mode remains the explicit rollback path. Evidence: [Pi5 resource cap](./deployments/pi5-backup-resource-cap-2026-10-21.md) | done 2026-10-21 (observe next scheduled classes) |
| B11 | CouchDB about 80 percent CPU, 1.2 M requests in 72 h from two LiveSync clients | Data server should be quiet | The VictoriaMetrics baseline showed average 0.094 core, P95 0.086 core, max 0.682 core and max 145.9 MiB working set; the 2026-10-21 live spot check found 0.40% CPU, 123.3 MiB RSS, no active tasks, 14 `_changes` log mentions, no 5xx and no evidence of tight polling. No rate limit or client change is justified. Evidence: [Pi5 runtime audit](./deployments/pi5-runtime-audit-2026-10-21.md) | done (continue passive monitoring) |
| B12 | Restore GitLab backup schedule after local purge | Local GitLab native payloads and staging archives were removed on VM100 on 2026-10-28, leaving only manifest/checksum/remote snapshot receipts. Re-enable the off-host GitLab backup timer, run one fresh backup, verify the remote snapshot and restore marker, then set retention. | open |
| B13 | Cap VM100 Docker logs | GitLab and an exited n8n container have about 4.9 GiB of Docker JSON logs. Configure service-level `json-file` rotation (target `100m` x `5`), redeploy safely, and verify the old logs are no longer growing. | Current GitLab and n8n containers report `json-file` with `max-size=100m` and `max-file=5`; exited historical tasks are not the active writers. | done 2026-10-31 |

## P2 Exposure and routing

| ID | Item | Why | How / verify | Status |
|---|---|---|---|---|
| E1 | `homelab` CouchDB (5.9 GB, admin-only) | LiveSync copy of this repo; not exposed on `sync-db` | Decision 2026-10-21: keep private/admin-only and do not add a public or remote `sync-db` route. Reopen only with a named non-admin consumer, `_security` policy, path restriction and restore test. | closed (2026-10-21 decision) |
| E2 | Catalog vs live drift | `catalog.yml` marked `couchdb`/`pgadmin` as `exposure: lan`; live file did not | Catalog regenerated and atomically published to Pi5; route smoke checks passed | done |
| E3 | `couchdb.` and `sync-db.` share a backend with split routers | Hand edit lives only on Pi5 | Split is now declared in the catalog with path restriction and shared service name; `sync-db/` 401 and `/_utils/` 404 verified | done |

## P2 Automation

| ID | Item | Why | How / verify | Status |
|---|---|---|---|---|
| A8 | GitLab CI deploy job with manual approval | Approval enforced by GitLab, not by Semaphore Community | Source contract added 2026-10-21 for release-ready Homepage: protected manual production job, immutable catalog digest, fixed forced-command SSH boundary, serialized resource group, file-backed protected variables, and Mezon receipt. Protected GitLab variables/environment plus one positive and one no-op live acceptance remain. Evidence: [GitLab CI Homepage approval](./deployments/gitlab-ci-homepage-approval-2026-10-21.md) | partial (live enrollment pending) |
| A2 | Nightly drift job | Catch live-vs-repo drift | Three retired VictoriaMetrics scrape jobs were removed through the Pi5 manager path; Compose validation passed, VictoriaMetrics is ready, and `/api/v1/targets` has 14 active targets without them. VM100 now runs the existing read-only target audit daily and sends the result through the existing Mezon notifier; its one-shot service run passed and the timer is active. The restricted Pi5 observer now includes a manager-safe `swarm_services` probe, and Semaphore task `#149` verified 25 live Swarm services with `manager=true`, `ok=4`, `failed=0`, and `unreachable=0`. Evidence: [monitoring target drift](./deployments/monitoring-target-drift-2026-10-21.md), [monitoring drift scheduler](./deployments/monitoring-drift-scheduler-2026-10-21.md), and [Swarm service inventory probe](./deployments/monitoring-service-inventory-probe-2026-10-21.md). | done 2026-10-21 (continue scheduled observation) |
| A3 | Image updates | No pinned digests | Done 2026-10-21: VM100 runs pinned Diun in notify-only mode every 12 hours with read-only Docker socket, no published ports, and `0.25 CPU/256 MiB` limits. It sends update warnings to Mezon and never applies an image update. Evidence: [Diun image watch](./deployments/diun-image-watch-2026-10-21.md) | done 2026-10-21 (observe) |
| A4 | Break-glass path | GitLab runs on the infrastructure it deploys | Documented workstation/1Password SSH recovery, host-key verification, bounded operator command and return-to-automation procedure in `docs/runbooks/automation-operations.md` | done (operator procedure documented; credentials remain external) |
| A5 | Trim Semaphore | Stop expanding it | Done 2026-10-21: removed 14 retired Knowledge Hub templates through the authenticated API, retained seven operational templates, and preserved all 68 task-history records. Evidence: [template trim](./deployments/semaphore-template-trim-2026-10-21.md). | done (recheck after future experiments) |
| A6 | Reduce non-data workloads on Pi5 | Semaphore, provisioner, monitoring and registry share data-host resources | VM100 task `#150` baseline was reconciled one service at a time. All running VM100 containers now have non-zero CPU and memory limits. App canaries, worker/control-plane caps, Whiteboard, CouchLoom dependencies and Knowledge Hub Search were verified; AdGuard, edge Traefik and Rathole remain on Pi5 by operator decision. The orphan BDS tunnel was removed because no BDS origin exists on VM100. Evidence: [VM100 resource inventory closeout](./deployments/vm100-resource-inventory-2026-10-21.md). | done 2026-10-21 (continue high-water observation) |
| A7 | Remove retired VM100 host alias | `/etc/hosts` still named the VM `k8s-cp-1`, causing `sudo` resolution warnings after Kubernetes retirement | Done 2026-10-21: replaced it with `127.0.1.1 vm100-prod`; preserved a timestamped host-file backup and verified systemd/container health | done |

## Update candidates — 2026-10-29

This section began as a planning baseline. The 2026-10-31 controlled rollout is
now reconciled below; any row still marked `ready`, `decision`, `partial`, or
`blocked` remains outside the completed acceptance set. Every future rollout
must first capture the current digest, back up the relevant configuration/data,
deploy one service at a time, run the listed canaries, and keep a bounded
rollback to the previous digest.

| ID | Service / current image | Compatibility assessment and decision | Pre-deployment plan | Status |
|---|---|---|---|---|
| U1 | n8n + n8n-runners — `2.46.3` | Upgrade and runner compatibility are applied and healthy, but authenticated Code-node execution plus the planned gold-price/Mezon canaries are not evidenced in this ledger. | Keep the current pinned pair; add the missing authenticated canary receipts before closing. | partial (2026-10-31; runtime gate passed, authenticated canaries pending) |
| U2 | Knowledge Hub Search / SearXNG — `ghcr.io/searxng/searxng@sha256:f1bbc31c…` | Candidate digest applied; container is running and JSON search returned `200`. | Keep the pinned digest and config backup; no further action in this rollout. | done 2026-10-31 |
| U3 | NetBird dashboard — `v2.96.0` / `sha256:340b13c0…` | Updated as a compatible pair with U4; backup, `1/1`, public `200`, peer and relay checks passed. | Keep the paired versions and rollback evidence. | done 2026-10-31 |
| U4 | NetBird server — `0.82.0` / `sha256:7b5b53b2…` | Updated as a compatible pair with U3; API, peer and route checks passed. | Keep the paired versions and rollback evidence. | done 2026-10-31 |
| U5 | Databasus — `databasus/databasus:v3.64.0` | Upgrade applied after correcting 15 invalid `THREE_MONTH` retention values; runtime and Pi5 verification agent are healthy. | Verify login, all jobs, latest-success markers, Drive target and failure notifier; keep non-service jobs out of the restore wave until explicitly scoped; rollback to `v3.60.0` only if metadata or notifier checks regress. | partial (2026-10-31; approved service set complete) |
| U6 | CloudBeaver — `dbeaver/cloudbeaver:26.2.3` | Upgrade completed with workspace archive, login, private explorer, schema migration and public status `200`; no public DB exposure was added. | Keep the current workspace archive and rollback image. | done 2026-10-31 |
| U7 | Semaphore — `semaphoreui/semaphore:v2.19.17` | Upgrade and runner connection passed; the required post-upgrade no-op task receipt is not explicit in the ledger. | Capture one bounded no-op task receipt, then close. | partial (2026-10-31; no-op receipt pending) |
| U8 | Family Tree — `oven/bun:1-slim` | Mutable tag and Diun signal, but no trusted deployed digest comparison. Bun runtime changes can break the application. Decision: **do not roll out until the tag is pinned and app tests pass**. | Resolve current/candidate digests; build or stage with lockfile; run application health and representative CRUD tests; deploy one task; verify logs and persistence; rollback to the recorded digest. | blocked |
| U9 | RelayHub Redis — `redis:7.4-alpine` | Persistence and application smoke passed after the pinned runtime was reconciled, but queue behavior and latency acceptance are not recorded. | Add queue/reconnect and bounded latency receipts before closing. | partial (2026-10-31; queue/latency gate pending) |
| U10 | Backup relay Nginx — three `nginx@sha256:56168782…` containers | Diun produced repeated signals, but the observed digest was also the deployed digest; no pending update is proven. Decision: **no rollout**. | Reconcile Diun state with registry manifest; if a real candidate exists, test PostgreSQL/CouchDB/CouchLoom relay downloads and backup checksums before one-at-a-time replacement. | blocked |
| U11 | Diun — pinned `crazymax/diun@sha256:e324…` | Diun is healthy but has 15–16 registry failures per scan, so its update decisions are incomplete. Decision: **do not update Diun; fix observability first**. | Repair authenticated/private registry access without exposing credentials; verify public registry checks and notifier delivery; only then assess a Diun image update with a pinned digest and health check. | blocked |
| U12 | Private/local application images — MyPocket, Homepage, Provisioner, Semaphore Runner, RelayHub, CouchLoom, macOCR, OpenClaw, K8s Syntax, Mezonhook, Whiteboard | Registry authentication/403/502 and local image tags prevent a trustworthy compatibility assessment. Decision: **no update decision yet**. | Repair registry visibility; generate current-vs-candidate digest inventory from source commits; run service-specific smoke tests and backup checks; create one follow-up backlog item per confirmed candidate before rollout. | blocked |

## P3 Later

| ID | Item | Status |
|---|---|---|
| L1 | Decide on a data VM after measuring Proxmox capacity | Decision 2026-10-21: keep Pi5 as the DB/data host; VM100 remains the production compute and backup/restore worker. Reconsider only after a separately funded failure-domain host or storage target exists. | closed (2026-10-21 decision) |
| L2 | pgBackRest with WAL archiving to a VM100 repo host (PITR) | Keep daily logical backup only for now; PITR is deliberately out of scope | closed (2026-10-21 decision) |
| L3 | Postgres collation-version warning (`ALTER DATABASE ... REFRESH COLLATION VERSION`, then reindex) | done 2026-10-21: refreshed and reindexed maintenance database `postgres` only; stored and actual versions now match at `2.36`, and all application databases remained connectable. Evidence: [collation reconciliation](./deployments/postgres-collation-reconciliation-2026-10-21.md) |
| L4 | Decommission legacy Pi `/ssd-data/backup/simple-backup.sh` after B1 passes | done 2026-10-21: verified its cron entry is commented/disabled, no legacy process is running, and the obsolete script was removed after B1 restore acceptance; current systemd backup timers remain the sole scheduler |
| L5 | DB operations worker VM | VM110 `db-ops` at `10.10.0.32` now has 4 vCPU/8 GiB/80 GiB, SSH, passwordless sudo, guest agent, restic/rclone and no scheduler; production backup runtime has not moved | Import/no-op IAC proof, package the existing runtime, then migrate one backup class at a time with rollback observation |

Detailed phased plan for B1 to B8: [backup-hardening-plan-2026-10-20.md](./deployments/backup-hardening-plan-2026-10-20.md).

## Backup assessment, 2026-10-20

Works today: five timer-driven classes on VM100 (databases, database-instances, GitLab, RustFS,
retention), encrypted upload to Drive, and all five last runs succeeded (retention at
2026-10-20 03:00 UTC); VM100 has 43 GB free. Weaknesses: one remote target, no completed restore
drill, no configs or VM image backup, health check failed two days running (disk full on
18th, lock held on 19th) with no alert, and the Pi5 has no scheduler of its own, so it depends on
VM100 being healthy. The bespoke chain (systemd, provisioner, Semaphore, rclone, restic) is
harder to operate than a standard tool. Simplification options for B3 to B8: Proxmox Backup Server
for VMs plus Backrest or Kopia over restic for files and dumps, with native dumps kept.

## Operating notes

- The auto-mode classifier blocks SSH writes to production hosts. Allow rules live in
  `.claude/settings.local.json` (gitignored). Prepared scripts: `pgnet-step-a.sh`,
  `pgnet-step-b-whiteboard.sh`, `pgnet-step-c-gitlab.sh`, `pgnet-step-d-detach.sh`; copy them into
  `automation/` before the session scratchpad is cleaned.
- Done in this rollout: legacy tunnel ports blocked, SSH key-only, coturn limits, `pg-net` and
  `s3-net` and `couchdb.` LAN-only, `sync-db` path-restricted, pgbouncer, whiteboard and
  GitLab moved to `pg-net`.
---
