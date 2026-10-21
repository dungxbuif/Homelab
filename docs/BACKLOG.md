---
type: Reference
title: "Homelab Backlog"
description: "Consolidated open work from the 2026-10-19/20 audit and network-hardening rollout, ordered by priority"
timestamp: 2026-10-20T00:00:00+07:00
---

# Homelab Backlog

Sources: [network, workload and automation audit](./research/network-workload-automation-audit-2026-10-19.md),
[network hardening rollout](./deployments/network-hardening-2026-10-19.md),
[backup runbook](./runbooks/backup-restore.md), and the 2026-10-20 operating session.
Status values: `open`, `ready` (script prepared, not run), `blocked`, `decision`.

## P0 Security

| ID | Item | Why | How / verify | Status |
|---|---|---|---|---|
| S1 | Public GitHub repo exposes credentials | Credentials in history are compromised regardless of repo state | Rotate every exposed secret, then purge or privatise; record in LOG | open (rotation deferred) |
| S2 | Root cause of the VPS HostSNI edit outage | Removing one hostname from `/root/gateway/dynamic.yml` took sites down for 3 to 4 minutes | Reproduce on a copy or in a window with Traefik logs open; failing file kept at `/root/firewall-backup/dynamic.yml.broken-attempt` | open |

## P1 Network segmentation

| ID | Item | Why | How / verify | Status |
|---|---|---|---|---|
| N1 | Detach `homelab-net` from `postgres` | Shared flat network exposes Postgres to every service on it | Applied 2026-10-20: backed up compose, removed the source declaration, detached the endpoint, terminated one legacy PgBouncer backend session, verified all DB clients on `10.0.30.x`, Postgres healthy and four production routes 200. Backup: `/ssd-data/infra/docker-compose.yml.bak-pg-detach-20261020-214540` | done |
| N2 | Flush old pgbouncer server connections | App clients can retain PgBouncer connections on `homelab-net` during migration | Done 2026-10-20: NetBird and macOCR migrated to `pg-net`; legacy `172.30.0.91/.92` sockets are gone and DB sessions use `10.0.30.4` | done |
| N3 | relayhub reaches PgBouncer via LAN `10.10.0.5:5432` | Host port stays published only for this client | Done 2026-10-20: API and worker use `pgbouncer:6432` on `pg-net`; API also uses `edge-http-net`; both healthy and public `/readyz` 200 | done |
| N4 | Bind remaining host-published datastore ports | Datastores and monitoring APIs should not listen on all interfaces | Done 2026-10-20: PgBouncer `5432`, Redis `16379`, VictoriaMetrics `8428`, and Alertmanager `9093` bind only to `10.10.0.5`. Health/API probes passed and production route smoke checks remained healthy. | done |
| N5 | Keep `homelab-net` only where `redis-prod` is needed | The shared network is still a broad lateral-access boundary | Completed 2026-10-20. Production apps and GitLab tunnels were migrated one at a time. Documented exceptions are CouchLoom for Pi5 CouchDB DNS, plus Pi5 edge/data/control-plane services: Traefik, PgBouncer, RustFS, registry, Redis, pgAdmin and provisioner. | done (documented exceptions) |
| N6 | Compose drift on Pi5 | Live RustFS/CouchDB endpoints had networks missing from the source Compose file | Done 2026-10-20: declared live RustFS and CouchDB edge/data networks; `docker compose config` passed; no service recreate. Backup: `/ssd-data/infra/docker-compose.yml.bak-compose-reconcile-20261020-155327` | done |

| A1 | Complete AI model rollout verification | Selector rollout is complete; real business inference quality is not yet measured | `mypocket-worker` was updated on the Pi5 manager with `start-first`; Docker reported `update completed`, the new task is running, the model audit passes all five selectors, and Money `/api/v1/health` returned 200. Real business-inference quality UAT remains. Evidence: [worker model release](./deployments/mypocket-worker-model-release-2026-10-21.md) | partial (runtime rollout done; quality UAT remains) |

## P1 Backup (see assessment below)

| ID | Item | Why | How / verify | Status |
|---|---|---|---|---|
| B1 | Remote Drive restore acceptance | Backups are unproven until a full restore works | Passed all four current backup classes: `database-instances` PostgreSQL 17/pgvector restore with 226 relations; GitLab native archive and SQL restore with 928 relations, 3 users and 5 projects; shared `databases` payload checksums plus native `bds_prod` and CouchDB `obsidian_vault` restores; RustFS payload checksums plus `mac-ocr` S3 restore with 62 objects. Evidence: [GitLab](./deployments/gitlab-restore-acceptance-2026-10-21.md), [databases](./deployments/databases-restore-acceptance-2026-10-21.md), [RustFS](./deployments/rustfs-restore-acceptance-2026-10-21.md). Full GitLab application boot remains an optional higher-cost drill; monthly unattended restore is B8. | done 2026-10-21 |
| B2 | Backup of host configs | Compose files, Traefik, Caddy, `/etc`, secrets are not a backup class | Done 2026-10-21: encrypted `configs` snapshot uploaded to Drive, Restic integrity check passed, and local-mirror scratch restore checksum passed. Timer enabled after acceptance. | done |
| B3 | VM100 vzdump | VM-level recovery has no image | Read-only Proxmox preflight 2026-10-21: VM100 is running with 6 vCPU/16 GiB/200 GiB; only `pre-docker-ce-20261014` exists; `local` has 89.8 GB free and `local-lvm` 100.0 GB free; no PBS/NAS storage is configured. Evidence: [vzdump preflight](./deployments/vm100-vzdump-preflight-2026-10-21.md). Add a separate failure-domain target before creating the first image backup. | open (target required) |
| B4 | Dead-man's switch and alerts | A silent scheduler failure goes unnoticed | VM100 health parses Pi5 output and turns missing/stale/invalid success markers into a Mezon failure; restore-drill marker age is checked; and the VPS now runs an independent five-minute HTTPS heartbeat for the public homelab path with transition-only Mezon alerts. Evidence: [dead-man hardening](./deployments/backup-deadman-alerts-2026-10-21.md) and [external VPS heartbeat](./deployments/external-heartbeat-vps-2026-10-21.md). | done 2026-10-21 (continue observing) |
| B5 | Health check false negatives | 2026-10-19 health failed only because retention held the lock for 45 minutes | Lock-aware health deployed to VM100 and Pi5; upload confirms snapshot metadata immediately, while structural checks run in retention and Sunday deep-verify reads 10% of packs; schedules are spaced after observed DB runtime. Live health recheck passed with all timers enabled/active and the lock free. | done (continue observing weekly verify) |
| B6 | VM100 disk pressure | On 2026-10-18 only 105 MB was free: GitLab backup and retention failed | Maintenance policy is active; health warns at 85% and fails at 92%. The monthly restore payload, stale runtime candidates, old stopped containers and 11 anonymous Docker volumes were removed only after reference checks. GitLab restore acceptance is complete, so local GitLab staging now keeps one complete run; removing the older 8.2 GiB run reduced VM100 to about 36 GB free / 82% used. The named `mypocket-prod-backups` volume was retained. Unreferenced Whiteboard rollback tags were reviewed against manager service state and removed. Daily maintenance uses a seven-day age threshold, keeps 5GB of BuildKit cache, never prunes volumes, and a recheck reclaimed `0B` because remaining cache is recent or referenced. Evidence: [disk audit](./deployments/vm100-disk-audit-2026-10-21.md) and [orphan cleanup](./deployments/vm100-docker-orphan-cleanup-2026-10-21.md). No broad Docker prune is justified. | done 2026-10-21 (continue disk observation) |
| B7 | Second off-site target | Google Drive is the only remote copy | Add a second restic repo (B2, Hetzner box or LAN NAS) for 3-2-1 | decision |
| B8 | Monthly automated restore test | Replaces manual checks | `homelab-backup-restore-drill.timer` restores the latest `databases`, `database-instances`, `gitlab`, and `rustfs` snapshots into a disposable path, checks manifests/checksums, writes a success marker, and notifies Mezon; evidence: [acceptance](./deployments/backup-restore-drill-acceptance-2026-10-21.md) | done 2026-10-21 |
| B9 | Make Pi5 passive for backups | Pi5 runs export, restic upload, check and prune and holds restic and Drive secrets | Phase 2.5 deployed and verified 2026-10-21: VM100 owns retention and weekly integrity for `databases`/`rustfs`; Pi5 exports/uploads and serves read-only markers. The VM100 private network preflight now passes for `pgbouncer:6432`, `rustfs:9000`, and `couchdb:5984` by Docker DNS. Phase 7 still moves exports and secrets off Pi5 after a one-week native-export comparison. Evidence: [VM100 retention ownership](./deployments/backup-retention-vm100-2026-10-21.md) and [backup pull network preflight](./deployments/backup-pull-network-preflight-2026-10-21.md). | partial (retention and network path ready; export/secret removal pending) |
| B10 | Cap any remaining Pi5 backup job | Protect the data server's latency | Deployed `run-pi-capped.sh`, `pi-executor.sh` and `pi-ssh-guard.sh` through Semaphore task `#144`; current mode is portable `nice/ionice`, with strict systemd-scope mode retained for a later privileged wrapper. Evidence: [Pi5 resource cap](./deployments/pi5-backup-resource-cap-2026-10-21.md) | partial (portable deployed; systemd cap pending) |
| B11 | CouchDB about 80 percent CPU, 1.2 M requests in 72 h from two LiveSync clients | Data server should be quiet | The VictoriaMetrics baseline showed average 0.094 core, P95 0.086 core, max 0.682 core and max 145.9 MiB working set; the 2026-10-21 live spot check found 0.40% CPU, 123.3 MiB RSS, no active tasks, 14 `_changes` log mentions, no 5xx and no evidence of tight polling. No rate limit or client change is justified. Evidence: [Pi5 runtime audit](./deployments/pi5-runtime-audit-2026-10-21.md) | done (continue passive monitoring) |

## P2 Exposure and routing

| ID | Item | Why | How / verify | Status |
|---|---|---|---|---|
| E1 | `homelab` CouchDB (5.9 GB, admin-only) | LiveSync copy of this repo; not exposed on `sync-db` | If remote sync is needed, create a non-admin `_security` member and add `PathPrefix(/homelab)` to the `sync-db` rule; review size or compact | decision |
| E2 | Catalog vs live drift | `catalog.yml` marked `couchdb`/`pgadmin` as `exposure: lan`; live file did not | Catalog regenerated and atomically published to Pi5; route smoke checks passed | done |
| E3 | `couchdb.` and `sync-db.` share a backend with split routers | Hand edit lives only on Pi5 | Split is now declared in the catalog with path restriction and shared service name; `sync-db/` 401 and `/_utils/` 404 verified | done |

## P2 Automation

| ID | Item | Why | How / verify | Status |
|---|---|---|---|---|
| A1 | GitLab CI deploy job with manual approval | Approval enforced by GitLab, not by Semaphore Community | Forced-command SSH key, job per stack | open |
| A2 | Nightly drift job | Catch live-vs-repo drift | Three retired VictoriaMetrics scrape jobs were removed through the Pi5 manager path; Compose validation passed, VictoriaMetrics is ready, and `/api/v1/targets` has 14 active targets without them. VM100 now runs the existing read-only target audit daily and sends the result through the existing Mezon notifier; its one-shot service run passed and the timer is active. The restricted Pi5 observer now includes a manager-safe `swarm_services` probe, and Semaphore task `#149` verified 25 live Swarm services with `manager=true`, `ok=4`, `failed=0`, and `unreachable=0`. Evidence: [monitoring target drift](./deployments/monitoring-target-drift-2026-10-21.md), [monitoring drift scheduler](./deployments/monitoring-drift-scheduler-2026-10-21.md), and [Swarm service inventory probe](./deployments/monitoring-service-inventory-probe-2026-10-21.md). | done 2026-10-21 (continue scheduled observation) |
| A3 | Image updates | No pinned digests | Renovate or Diun (notify only), `order: start-first`, healthchecks | open |
| A4 | Break-glass path | GitLab runs on the infrastructure it deploys | Documented workstation/1Password SSH recovery, host-key verification, bounded operator command and return-to-automation procedure in `docs/runbooks/automation-operations.md` | done (operator procedure documented; credentials remain external) |
| A5 | Trim Semaphore | Stop expanding it | Done 2026-10-21: removed 14 retired Knowledge Hub templates through the authenticated API, retained seven operational templates, and preserved all 68 task-history records. Evidence: [template trim](./deployments/semaphore-template-trim-2026-10-21.md). | done (recheck after future experiments) |
| A6 | Reduce non-data workloads on Pi5 | Semaphore, provisioner, monitoring, registry, pgAdmin, LibreSpeed share data-host resources | Move in order of risk (see plan Phase 8). AdGuard, edge Traefik and Rathole stay on Pi5 by operator decision; Orange Pi excluded. VM100 task `#150` confirmed the existing GitLab/KubeKosh/Stirling/runner/CouchLoom limits. Homepage uses `0.50 CPU/512 MiB` with start-first; macOCR uses `1 CPU/1 GiB` with stop-first; n8n uses `1 CPU/2 GiB` with stop-first; OpenClaw uses `1 CPU/2 GiB` with stop-first; MyPocket API uses `1 CPU/1 GiB` with stop-first; RelayHub API/worker each use `1 CPU/1 GiB` in persistent Compose config; NetBird dashboard uses `0.50 CPU/512 MiB` with start-first. These canaries passed route/readiness checks. MyPocket worker, NetBird server, NATS/Redis, and OCR worker remain uncapped pending workload-specific metrics. Evidence: [VM100 resource-cap baseline](./deployments/vm100-resource-cap-baseline-2026-10-21.md), [OpenClaw canary](./deployments/openclaw-resource-canary-2026-10-21.md), [MyPocket API canary](./deployments/mypocket-api-resource-canary-2026-10-21.md), and [RelayHub canary](./deployments/relayhub-resource-canary-2026-10-21.md). | partial (seven app canaries applied; stateful/worker candidates pending) |
| A7 | Remove retired VM100 host alias | `/etc/hosts` still named the VM `k8s-cp-1`, causing `sudo` resolution warnings after Kubernetes retirement | Done 2026-10-21: replaced it with `127.0.1.1 vm100-prod`; preserved a timestamped host-file backup and verified systemd/container health | done |

## P3 Later

| ID | Item | Status |
|---|---|---|
| L1 | Decide on a data VM after measuring Proxmox capacity | decision |
| L2 | pgBackRest with WAL archiving to a VM100 repo host (PITR) | decision, P2 now that Pi5 is a data server with a 24 h RPO |
| L3 | Postgres collation-version warning (`ALTER DATABASE ... REFRESH COLLATION VERSION`, then reindex) | open |
| L4 | Decommission legacy Pi `/ssd-data/backup/simple-backup.sh` after B1 passes | done 2026-10-21: verified its cron entry is commented/disabled, no legacy process is running, and the obsolete script was removed after B1 restore acceptance; current systemd backup timers remain the sole scheduler |

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
  `s3-net`, pgadmin and `couchdb.` LAN-only, `sync-db` path-restricted, pgbouncer, whiteboard and
  GitLab moved to `pg-net`.
