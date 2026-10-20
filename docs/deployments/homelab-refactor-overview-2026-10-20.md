# Homelab refactor overview, 2026-10-20

Status: execution checkpoint. Phase 1 capacity protection is partially applied;
the next mutation is intentionally held at the per-container Swarm logging
audit boundary.

## Target roles

- Pi5: PostgreSQL, PgBouncer, CouchDB, Redis, RustFS. AdGuard, Traefik and
  Rathole remain as approved edge exceptions. Orange Pi is excluded.
- VM100: applications, GitLab CI, backup execution, verification and monitoring.
- VPS: public ingress and existing relay/tunnel services.
- Google Drive: encrypted off-site backup using OAuth project
  `homelab-backup-488616`.
- No new VM or NAS in this rollout. Reconsider a backup VM only after measuring
  peak backup/restore resource usage. A VM on the same host/storage is not an
  independent backup copy.

## Already applied

- Removed 46 Dead Swarm task containers on VM100; all 32 running container IDs
  remained unchanged. Volumes were not deleted. Container records are removed;
  service definitions and persistent mounts remain for recreation.
- Docker accounting works again. Root usage changed from 79 to 76 percent;
  available space increased from about 43 to 48 GB.
- Installed `homelab-docker-maintenance.timer`: daily noon in Asia/Ho_Chi_Minh,
  up to five minutes jitter, skips if the shared backup lock is busy.
- Cleanup removes eligible Dead tasks, dangling images older than seven days,
  and old build cache with a 5 GB retention budget. Tagged rollback images and
  volumes remain. First manual service run completed with exit status 0;
  no additional image/cache bytes met cleanup criteria on this run.
- Metadata reports: `/var/lib/homelab-maintenance/` on VM100. Service output:
  `journalctl -u homelab-docker-maintenance.service`.
- Applied the first capacity-protection change: a journald drop-in caps
  persistent system logs at `1G`, keeps `20G` free on `/`, limits individual
  journal files to `128M`, and expires entries after `14 days`. It is applied
  without restarting Docker or application containers.
- Added a read-only Swarm logging audit for the manager. It reports services
  missing explicit `json-file` `max-size` and `max-file` values; it does not
  call `docker service update` or restart tasks.
- Completed network hardening item N1: PostgreSQL was detached from
  `homelab-net` after all observed clients were confirmed on `pg-net`; the
  legacy PgBouncer session was closed and recreated through `10.0.30.4`.
- Migrated NetBird as the first PgBouncer consumer: `netbird_netbird-server`
  now uses `pg-net` plus its edge/control networks, and its old six client
  sockets on `172.30.0.91` are gone.
- Migrated macOCR next: it now uses `pg-net`, `edge-http-net` and the new
  app-specific `macocr-redis-net`; OCR `/healthz` and `/docs/` returned 200.
- Migrated RelayHub API and worker from the Pi5 LAN DB endpoint to
  `pgbouncer:6432` on `pg-net`; API retained edge access through
  `edge-http-net`, both containers are healthy and public `/readyz` is 200.
- Narrowed the PgBouncer host bind to `10.10.0.5:5432`; Postgres stayed up and
  all checked production routes recovered after PgBouncer recreation.
- Narrowed the Redis host bind to `10.10.0.5:16379`; Redis returned `PONG` and
  the production route smoke checks remained healthy.
- Narrowed the VictoriaMetrics host bind to `10.10.0.5:8428`; LAN health and
  TSDB API probes returned 200 without changing its data volume.
- Narrowed the Alertmanager host bind to `10.10.0.5:9093`; health and API v2
  probes returned 200 without changing its configuration volume. N4 is now
  complete; the next network item is N5, retiring remaining `homelab-net`
  memberships one app at a time.
- Completed the first N5 application migration: MyPocket API and worker no
  longer use `homelab-net`; both resolve PgBouncer over `data-net` and Redis
  over `mypocket-redis-net`, while the API remains reachable through
  `edge-http-net`. Redis Compose persistence now declares the MyPocket overlay.
- Migrated NetBird dashboard, K8s Syntax and OpenClaw from `homelab-net` to
  `edge-http-net` (OpenClaw keeps its own state volume). NetBird's route was
  corrected to the actual service DNS name; OpenClaw's trusted proxy config was
  extended only for the edge overlay CIDR. All three public probes recovered.

## Remaining rollout

### Current verification notes

- Stirling's first `homelab-net` to `edge-http-net` update paused because
  Swarm `start-first` opened the bind-mounted H2 database twice. After scaling
  to zero, backing up the H2 file and settings, and applying `stop-first`, the
  service converged healthy on `edge-http-net`; public HTTPS returned HTTP 200.
  H2 backup directory: `/opt/apps/stirling-pdf/backups/network-migration-20261020-153254`.
- The AI audit found `mypocket-api` using the old `DeepSeek-V4-Flash` selector;
  production now uses `DeepSeek-V4.1-Flash` and its provider catalog, health and
  docs probes passed. `mypocket-worker` uses Qwen and was not changed. OpenClaw
  was subsequently moved to the verified FPT DeepSeek credential and now logs
  `fpt-deepseek/DeepSeek-V4.1-Flash`; its gateway, Telegram polling and public
  route recovered healthy. `whiteboard-backend` uses a separate DeepSeek
  endpoint and remains pending provider-specific model compatibility
  verification.
- NetBird backend routes were still using the retired `tasks.netbird-server`
  DNS name. Updated the live Pi5 Traefik dynamic file to
  `tasks.netbird_netbird-server`, backed it up, restarted the actual
  `edge-traefik-pi5` container, and verified public root `200`, unauthenticated
  API `401`, and backend-origin `404` instead of `502`.
- Whiteboard was moved from its separately failing DeepSeek endpoint to the
  verified FPT endpoint. Both `AI_MODEL_FAST` and `AI_MODEL_REASONING` now use
  `DeepSeek-V4.1-Flash`; the backend is healthy, `/healthz` is OK, and public
  HTTPS returns `200`. Real business inference remains the final UAT gate.
- Whiteboard frontend was then removed from `homelab-net` and recreated with
  only `edge-http-net` plus `whiteboard-app`; Compose validation passed,
  frontend health passed, and public HTTPS remained HTTP 200. Backup:
  `/opt/apps/whiteboard/docker-compose.prod.yml.bak-frontend-edge-20261020-153520`.
- KubeKosh was removed from `homelab-net` and recreated on `edge-http-net`.
  Its embedded `k8s-lab` node registered and became Ready, the API server was
  stable, and the public HTTPS route returned HTTP 200. Backup:
  `/opt/apps/kubekosh/docker-compose.yml.bak-edge-20261020-153646`.
- CouchLoom remains on `homelab-net` by design: its vault configuration uses
  the Docker DNS name `couchdb:5984` for the Pi5 CouchDB data service. Removing
  that membership without first introducing a dedicated CouchDB client network
  would break vault ingestion; this is an explicit dependency, not drift.
- GitLab was isolated from `homelab-net`: `gitlab_gitlab` now uses
  `edge-http-net`, `gitlab-net` and `pg-net`; the HTTPS, SSH, registry and
  HTTPS tunnel clients use `gitlab-net` only. Redis was attached to
  `gitlab-net` with a persistent Compose override, and GitLab returned HTTP 200
  after the long Omnibus restart.
- Reconciled Pi5 Compose source drift for RustFS and CouchDB network
  declarations against the live attachments; validation passed and no service
  was recreated. Backup: `/ssd-data/infra/docker-compose.yml.bak-compose-reconcile-20261020-155327`.

| Order | Work | Acceptance |
|---|---|---|
| 1 | Complete capacity protection: log limits, disk alerts, review retired images | Journald limit applied; remaining work is Docker per-container log policy, disk warning/failure tests and retired-image review |
| 2 | Fix backup health, schedule and lock handling; run check/prune on VM100 | No overlapping repository mutations; test real failures and busy-job states; Pi5 does no retention work |
| 3 | Restore latest Drive backups into isolated scratch containers on VM100 | PostgreSQL data and roles/grants, CouchDB attachments/deletions, RustFS objects and GitLab recovery verified; record versions, RPO/RTO |
| 4 | Pull backups from VM100 with native CLI/API; transition one class at a time | New backups restore successfully; capture newly created DBs, globals and RLS coverage; CouchDB changes feed or replication must preserve attachments and deletions |
| 5 | Move off-site credentials off Pi5 after validated cutover | Remove active env/files/mounts; rotate copied credentials; keep encrypted recovery material outside VM100; retire old runner after observation window |
| 6 | Alerts and encrypted configuration backup | Per-class success/failure, stale-backup detection, external heartbeat once destination configured, sample configuration restore |
| 7 | Network and placement cleanup | N1 complete; continue PgBouncer connection cleanup, consumer migration and host-port closure one app at a time |
| 8 | GitLab CI as deployment entrypoint, Ansible for host configuration; trim Semaphore | Reviewed plan/apply, deploy/rollback for one representative app, nightly drift report, documented workstation recovery |

Native backups remain: PostgreSQL `pg_dump` plus globals, CouchDB supported
export/replication, GitLab native backup plus separately inventoried config,
secrets and registry, RustFS S3 object access. Restic/rclone remain initially to
avoid changing repository format during hardening. Redis stays excluded.

## Execution corrections

- Remote scheduling alone is not a pull backup. Pi5 still incurs database read
  and query load when a remote `pg_dump` runs; client resource caps do not cap
  PostgreSQL backend CPU directly.
- `pg_read_all_data` does not bypass RLS. Validate complete restore and roles
  before accepting a least-privilege backup login.
- A nightly schedule targets roughly 24-hour RPO only while backups complete;
  failures increase RPO. PITR needs a base backup, uninterrupted WAL and alerts
  for archive failure/disk growth.
- About 1.2 million CouchDB requests in 72 hours is 4.6 requests/second overall,
  not proof of excessive polling. Diagnose endpoint latency, retries, indexing
  and compaction before changing clients or rate limits.
- Automatic cleanup retains tagged images. Ollama and Kubekosh were confirmed
  running and remain untouched despite older plan assumptions.

## Deferred decisions

PITR/pgBackRest, an independent backup disk or NAS, VM100 vzdump destination,
second off-site destination and external heartbeat account. Do not create paid
resources, skip GitLab artifacts or change edge placement implicitly.

## Rollout rule

One class/app at a time: record preflight, change, post-check and recovery path.
Keep current backup paths until replacement restores pass; never restore into
production. Full completion requires restore evidence and subsequent scheduled
runs, not merely a successful upload or checksum.

Detailed source plan: [backup hardening](backup-hardening-plan-2026-10-20.md).
