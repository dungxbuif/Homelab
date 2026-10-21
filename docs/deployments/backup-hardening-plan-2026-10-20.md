---
type: Plan
title: "Backup Hardening Plan (2026-10-20)"
description: "Detailed phased plan to fix backup alerting, disk pressure, lock overlap, retention proof, restore drills and config backup"
timestamp: 2026-10-20T00:00:00+07:00
---

# Backup Hardening Plan, 2026-10-20

Backlog items: B1 to B8 in [BACKLOG.md](../BACKLOG.md). Runbook: [backup-restore.md](../runbooks/backup-restore.md).
Runner code: `automation/backup-runner/`, `backup/scripts/`. Status: **implementation started; see execution record below**.

## Execution record, 2026-10-20

Review overview and corrections: [homelab-refactor-overview-2026-10-20.md](homelab-refactor-overview-2026-10-20.md).

- Applied: removed 46 Dead Swarm tasks; 32 running IDs unchanged. Docker
  accounting now works; root 76 percent used with about 48 GB available.
- Daily maintenance installed and enabled. First run exited 0; next run is
  2026-10-21 around 12:00 local time. Remaining rollout paused for review.

- Verification rerun 2026-10-20: `homelab-docker-maintenance.service` exited 0;
  no eligible Dead tasks were found, Docker accounting succeeded, and VM100 had
  52 GB free (74% used). The earlier lock-permission failure is historical; the
  current script opens the shared lock read-only before flocking it.
- Repository checks rerun after the maintenance/config reconciliation:
  `test_health_reporting.py`, scheduler contract, runner contract and retention
  gate tests all passed. These validate the local backup control flow; they do
  not replace a real Drive restore drill.

- Live follow-up 2026-10-20 20:02 UTC: the scheduled GitLab run
  `gitlab-20261020-190208` completed its 8.74 GB native archive export and
  Restic upload, then entered the mandatory structural repository check. The
  unit remained `activating` with no failed result and no success marker yet;
  cleanup was deliberately deferred until the check and post-check marker
  complete. VM100 was at 87% used with about 26 GB free. The image review found
  tagged rollback images and a stopped family-tree container reference; no
  image was removed during an active backup. This is evidence for B6, not a
  completed cleanup acceptance.

- Implementation prepared and verified locally: `upload-restic.sh` now defaults
  to `RESTIC_PREFLIGHT_MODE=config` and `RESTIC_POST_UPLOAD_CHECK=snapshot`.
  It verifies repository config and takes the snapshot ID from Restic's backup
  summary, avoiding repeated remote index enumeration. The previous inline
  structural path remains opt-in as `RESTIC_POST_UPLOAD_CHECK=structural`, and
  `RESTIC_PREFLIGHT_MODE=snapshots` is available for an explicit metadata
  preflight. Bash 3.2 compatibility was covered because the check helper no
  longer expands an empty array under `set -u`; upload immutability and Restic
  contract tests pass.

- Transport acceptance completed 2026-10-21: the database-instances retry
  succeeded with snapshot `164f85eb25e03f936a9cba0c29185d00712bf4cfbc155d1818726224ea3e72c7`.
  `restic-lib.sh` is deployed to VM100 and Pi5 with a `100ms` Drive pacer and
  burst `1`; the historical `10s` default remains an explicit override only.
  GitLab run `gitlab-20261020-190208` passed native archive checksums 4/4 and
  remote snapshot metadata verification (`a0cbb341f856d2ef324cb57b4ddb29dc4eab23f22c6909e9c0d131531cac26fb`).
  The success marker and Mezon notification were restored, one old completed
  staging run was removed, and VM100 ended at 83% used / 34GB free. The next
  scheduled cycles remain the observation gate for B5.

- Operator approved implementation. AdGuard, edge Traefik and Rathole stay on Pi5;
  they are explicit exceptions to the data-server rule. Orange Pi is excluded.
- First operation: remove only stopped, Dead Swarm task containers on VM100 using
  `automation/maintenance/cleanup-dead-tasks.py`. Preview records selected IDs,
  mounts and writable-layer change counts; apply saves metadata without environment
  secrets and refuses candidates with changed writable files or inspection errors
  other than the known missing-layer error. Volumes and images are not removed.
- Verification: compare running container IDs, inspect remaining Dead tasks, run
  `docker system df` and measure free space. Container records cannot be undeleted;
  Swarm recreates tasks from service definitions and persistent mounts remain.
- Baseline: root 79 percent used, 43 GB available; Docker accounting fails on task
  `1711725e6d25` with `rw layer snapshot not found`.
- Later phases remain pending. Public docs do not change: this is an internal
  maintenance workflow with no public API or application behavior change.
- Recurring cleanup approved: `homelab-docker-maintenance.timer`, daily 12:00
  Asia/Ho_Chi_Minh. Uses the backup flock; busy backup means skip until the next
  day. Remove eligible Dead tasks, dangling images older than seven days, and
  old build cache while retaining 5 GB. Keep tagged rollback images and volumes.
  Service limits: one CPU, 512 MB, low IO priority, 30-minute timeout. Verify a
  manual first run and timer next-run time. Rollback: disable timer and remove
  its unit/script files; cache is rebuildable, removed container records are not.

## 0. Facts established on 2026-10-20 (read-only checks)

| Fact | Evidence |
|---|---|
| Retention exists and is scheduled | `backup/policies.yaml`: 14 daily, 8 weekly, 12 monthly per class; `homelab-backup@retention.service` last succeeded 2026-10-20 03:00 UTC |
| Retention is gated | `run-retention.sh` refuses to run unless the `databases`, `rustfs`, `gitlab` success markers are younger than 26 h; a failed class deletes its own marker (`run-class.sh`) |
| Local staging is pruned | `cleanup-local-runs.sh` keeps the 2 newest complete runs per class (`BACKUP_LOCAL_RUN_KEEP=2`) after all repo checks pass; incomplete runs are never auto-removed |
| Staging is not the main disk consumer | `/opt/apps/homelab-backup/runs` is 17 GB: two GitLab runs of 8.2 GB each plus 27 MB instance dumps. VM100 `/` is 194 GB, 152 GB used (78 percent) |
| Disk was nearly full on 2026-10-18 | Health log: `free_bytes=105639936`, GitLab backup and retention failed |
| Health is red for the wrong reason | 2026-10-19 06:15 health ran while retention (05:30 start, about 4.5 h: `restic check` loads indexes and checks all packs) held the global lock |
| Timeline overlaps | GitLab native backup 02:30 to about 05:52 local (3 h 20 min), RustFS 04:30 to 05:11, retention 05:30 to about 10:00, health 06:15 |
| Disk consumers measured (`sudo du`) | `/var/lib/containerd` 69 GB, `/var/lib/docker` 34 GB (`rootfs` 28 GB, `containers` 5.6 GB, `volumes` 0.5 GB), `/opt/apps/gitlab/data` 36 GB, `/var/log` 3.9 GB, `/home` 3.2 GB, GitLab logs 0.9 GB. Docker plus containerd is about 103 GB of the 152 GB used |
| Stale Docker state | About 20 containers in `Dead` state (old swarm tasks of mypocket, netbird, openclaw, family-tree, macocr, k8s-syntax, mezonhook, tunnel clients), plus `tmpfs-repro-repro-1` in `Created` and an exited `pg-net-anchor` task; `docker system df` errors on `rw layer snapshot not found` |
| Large images, none tied to a running container in the list | `ollama/ollama:0.34.0` 9.2 GB, `educates-base-environment:3.8.0` 5.3 GB, `node:24-bookworm` 1.6 GB, `zeborg/kubekosh` 1.6 GB, untagged `semaphore-runner` 0.8 GB (to be confirmed unused before removal) |
| Docker on VM100 is unhealthy | `docker system df` fails: `rw layer snapshot not found for container 1711725e...`; VM rebooted about 2026-10-19 16:30 local, cause unknown |
| Only Google Drive holds remote copies | Three restic repos under `homelab-backups/{databases,gitlab,rustfs}`; no second target, no restore drill, no host-config class, no VM image |

Answers to the three questions raised: (1) spacing the jobs did not prevent the 2026-10-18 failure because the cause was
free space, not overlap; the overlap problem is separate (section 3). (2) Yes, retention for backed-up databases is
configured and ran successfully, but its effect is **unproven**: no snapshot count per repo has been compared with the policy
(Phase 1.4). (3) This document is that plan.

## Design principle (revised): Pi5 serves data and retained edge services

Pi5 (7.7 GB RAM, load 0.4, 39 percent disk) must only serve data: PostgreSQL, PgBouncer, CouchDB, RustFS, Redis. Backup,
verification, backup secrets and control services should live on VM100, which has 15 GB RAM and runs every application.
AdGuard, edge Traefik and Rathole remain on Pi5 by operator decision. No Orange Pi migration is planned.

Current state against that principle:

| Concern | Today | Target |
|---|---|---|
| Backup compute | Pi5 runs data exports/uploads; VM100 now runs `restic check`, `forget --prune` and `check --read-data-subset` for `databases` and `rustfs` | VM100 runs upload, check and prune; Pi5 only exports/uploads and answers marker queries |
| Backup secrets | restic password and rclone Drive token in `/ssd-data/infra/backup/runner.env` on Pi5 | Only on VM100 |
| Scheduler | VM100 timers call Pi5 through a forced-command SSH guard (good, already pull-style) | Keep; shrink what the guard allows |
| Non-data services on Pi5 | AdGuard, edge Traefik, Rathole, Semaphore and provisioner (swarm node `rpivn`), VictoriaMetrics, Alertmanager, blackbox, SNMP and cAdvisor exporters, registry, pgAdmin, LibreSpeed | Out of scope here; tracked as A6 and Phase 8. No new non-data service is added to Pi5 by this plan |
| Anomaly | CouchDB at about 80 percent CPU during the check; about 1.2 million requests in 72 h from two LiveSync client IPs | Investigate (Phase 1.6) |

Rules for every phase: add nothing to Pi5 except read-only paths and, temporarily, one resource-capped export; do not run Kuma,
restore drills or verification on Pi5; wrap any unavoidable Pi5 job in `systemd-run --scope -p CPUQuota=100% -p MemoryMax=1G
-p IOWeight=50` plus `nice -n 10 ionice -c3`.

## Execution constraints

- All VM100 and Pi5 writes need `ssh` write access; the auto-mode classifier blocks them even with allow rules, so each phase
  ships as a script (`bash -s` over ssh) that backs up what it touches, prints verification, and states rollback.
- One phase at a time; stop on any red verification. Do not edit the `/root/gateway/dynamic.yml` allow-list (S2).
- Never run retention or `restic forget/prune` by hand against production repos.

## Phase 1: Disk and retention proof (B6, B1 prerequisite). Effort 2 h. Risk low.

Goal: know what fills VM100, stop it filling again, and prove retention prunes.

1.1 **Measure.** `sudo du -xh --max-depth=2 /var/lib/docker /var/lib/containerd /var/log /opt/apps /home | sort -rh | head -30`
(use `nice`, run in background; a first attempt exceeded 120 s). Record the top ten consumers in this note. Expected suspects:
Docker image layers and build cache, `/var/log` (3.9 GB seen), GitLab data volume, restic temp caches in `/tmp/restic-check-cache-*`.

1.1b **Remove stale Docker objects (largest expected win, tens of GB).** List: `docker ps -a --filter status=dead --format '{{.ID}} {{.Names}}'`;
remove each Dead container (`docker rm -f <id>`; the rw-layer error container `1711725e6d25` is one of them) and `tmpfs-repro-repro-1`.
Then `docker images -a` against running containers: for every image with no container, record it, and remove after review
(`docker rmi`), starting with `ollama`, `educates-base-environment`, `node:24-bookworm`, and verified stopped Compose-era containers. Do not use `docker system prune -a --volumes`.
After removal measure `/var/lib/containerd` and `/var/lib/docker/rootfs` again (the `rootfs` 28 GB may be nested k3s containerd
data, see the `.../var/lib/rancher/k3s/...` paths in the `du` error); identify which container owns it with
`sudo ls -la /var/lib/docker/rootfs/overlayfs/` and `docker inspect`.

1.2 **Fix the Docker record error.** `docker ps -a --format '{{.ID}} {{.Names}} {{.Status}}'`; remove the container whose
layer is missing (`docker rm -f 1711725e6d25...`, confirm it is not a swarm task first with `docker inspect`). Re-run `docker system df`.
Investigate the reboot: `last -x reboot shutdown`, `journalctl -b -1 -n 200 --no-pager`, Proxmox task log for VM 100.

1.3 **Cap known growers.** (a) journald: `SystemMaxUse=500M` in `/etc/systemd/journald.conf.d/size.conf`, `journalctl --vacuum-size=500M`.
(b) Weekly Docker cleanup timer: `docker image prune -af --filter until=168h` and `docker builder prune -f --filter until=168h`
(never `volume prune`). (c) `BACKUP_LOCAL_RUN_KEEP=1` for the GitLab class only (saves 8.2 GB) once Phase 5 restore drill has passed;
keep 2 until then. (d) `restic` cache dirs: set `RESTIC_CACHE_DIR=/var/cache/restic` and delete `/tmp/restic-check-cache-*` older than 2 days.

1.4 **Prove retention.** From VM100 using the existing restic container wrapper (`backup/scripts/run_restic_container.py`),
read-only: `restic snapshots --compact` and `restic stats --mode raw-data` for each of the three repos. Expected: at most
14 + 8 + 12 snapshots per class (fewer while the history is young), and repo size stable between two days. Record counts and
sizes here. If counts exceed policy, inspect `backup/scripts/verify-retention.sh` and the `forget` flags before changing anything.

1.5 **Alert on disk.** Extend `backup/scripts/check-backup-health.sh`: warn at 85 percent used on `/`, fail at 92 percent, keep the
existing low-free-space byte threshold. Message to Mezon via `notify-mezon.sh`.

1.6 **Pi5 load check (read-only).** `docker stats` for CouchDB, `docker logs --since 1h couchdb | grep -c '_changes'`, client IPs
from the access log. If LiveSync clients poll in a tight loop, fix the client (Obsidian LiveSync sync interval, `Use longpoll`)
and consider a CouchDB `max_dbs_open`/rate limit at Traefik. Record request rate before and after.

Acceptance: top consumers documented; `docker system df` works; `/` below 70 percent after cleanup; snapshot counts match policy;
health reports the new thresholds. Rollback: remove the drop-ins and timer; no data deleted except pruned images and journals.

## Phase 2: Schedule and health without false alarms (B5). Effort 2 h. Risk low to medium.

Problem: the nightly lock chain is serial and long, and health runs inside it.

2.1 **Retention cadence.** Replace the nightly 4.5 h full check with: nightly `restic check` (structure only, minutes) plus
`forget --prune` after a successful night; a weekly (Sunday 09:00 local) `restic check --read-data-subset=10%`. The upload and retention
scripts now default to the structure-only check; `RESTIC_READ_DATA_SUBSET=1/10` is an explicit opt-in for the deep window. The
`homelab-backup-verify-weekly.timer` runs the explicit deep check across Pi5 and VM100 repositories under the global lock.
Files: `automation/backup-runner/run-retention.sh`, `backup/scripts/verify-retention.sh`, `systemd/homelab-backup-retention.timer`,
new `homelab-backup-verify-weekly.timer`.

2.2 **New order (local time).** 01:00 databases, 03:00 database-instances, 04:00 RustFS, 05:00 GitLab, 10:00 retention light,
12:00 health, 13:00 configs, and Sunday 09:00 deep verify. The spacing reflects the observed 90-105 minute database runtime and
prevents a long GitLab export from colliding with retention or health.

2.3 **Lock-aware health.** **Done 2026-10-20.** In `check-backup-health.sh`, if the global lock is held or a backup unit is `activating`, print
`state=running runtime=Ns` and exit 0 unless runtime exceeds a class limit (databases 30 min, GitLab 5 h, RustFS 90 min,
retention 90 min, deep verify 8 h). Only stale markers (older than 26 h) and failed units fail.

2.4 **GitLab wall time.** Investigate why the native backup takes 3 h 20 min for 8.2 GB (compression, `STRATEGY=copy`, skipped
content `SKIP=builds,artifacts` if acceptable). Record before changing.

2.5 **Move check, prune and verification for the Pi repos to VM100.** **Deployed 2026-10-21.** Restic works on the remote Drive repo from any host, so
`databases` and `rustfs` retention does not need Pi5. Steps: (a) copy the restic password and rclone config for those two repos to
VM100's existing private backup env (root-owned, mode 600), never into git; (b) copy the two success markers to VM100
(`run_pi` already streams the GitLab marker the other way; invert it: Pi writes markers, VM100 reads them over the forced-command
guard with a new read-only `markers` command); (c) change `run-vm100-scheduled.sh retention` to run `verify-retention.sh databases` and
`rustfs` locally instead of `run_pi retention`; (d) add the read-only `markers` command to the Pi guard and publish both current and
historical guard/executor aliases. Keep one global lock on VM100 only. The live marker path and SHA checks passed; retention was then
verified for all four repositories after a stale `database-instances` lock was safely removed. Verify with `journalctl` that no
`restic check` runs on Pi5.

Acceptance: three consecutive nights with health exit 0 and no overlap in `journalctl`; a forced stale marker still turns it red.
Rollback: restore the previous timer files from git and reload systemd.

## Phase 3: Dead-man's switch (B4). Effort 3 h. Risk low.

3.1 Run Uptime Kuma on **VM100** (a small compose service, not on Pi5; the instance in `/ssd-data/infra/kuma-data` on Pi5 can be retired
later under A6): create one **push monitor** per class
(databases, database-instances, gitlab, rustfs, retention) with a 26 h heartbeat (retention 8 days for the weekly deep verify) and
a Mezon notification channel. Each class pings its push URL at the end of `run-class.sh` only after the success marker is written;
URLs live in the existing secret env file, never in git.

3.2 Kuma on VM100 also watches Pi5 from outside (TCP 5432 via PgBouncer, HTTP to CouchDB and RustFS, ping), so Pi5 needs no agent. Add one external heartbeat: a single daily `curl` from VM100 to a
free external check service after health passes, with its own email or push channel. This covers Pi5 or LAN loss.

3.3 Add a Mezon message on **every** failed class (exists). Health notifications are warning/failure-only as of 2026-10-21; success summaries are disabled to avoid alert noise. A temporary observation window may explicitly set `BACKUP_HEALTH_NOTIFY_SUCCESS=true`; ad-hoc checks stay quiet by default.

Acceptance: disable one timer for a day in a test window; both Kuma and the external check alert. Rollback: remove the `curl` lines.

## Phase 4: Restore drill, then automate (B1, B8). Effort 4 h first run, 2 h to automate. Risk low (scratch only).

4.1 Scratch target on VM100 only (never on Pi5, never restoring over production, and read from Drive at a capped rate): a throwaway Postgres 16 (pgvector image used in prod) and CouchDB container on VM100 with no published ports
and a dedicated network, data under `/opt/apps/restore-drill/` with 20 GB free check first.

4.2 Restore with existing tools: `backup/scripts/restore-staging.sh`, `restore-database.py` for the latest snapshot of each repo
(Drive to staging to scratch). Never overwrite production.

4.3 Compare: per database, table list and `count(*)` of the five largest tables against production; CouchDB `doc_count` of
`obsidian_vault` and `homelab`; GitLab: restore the native archive into a scratch container, check `gitlab-rake gitlab:check`
and project count. Record RTO (wall time) and RPO (snapshot age).

4.4 Automate monthly: systemd timer on VM100 running the drill unattended with a pass or fail marker, pinged to Kuma (Phase 3).
`restore_test_days: 30` already exists in `backup/policies.yaml`; enforce it in health.

Acceptance: written report in `docs/deployments/` with RTO and RPO; marker age under 31 days. Rollback: delete the scratch directory.

## Phase 5: Configuration backup class (B2). Effort 3 h. Risk low.

5.1 Inventory to cover (encrypted by restic, so secrets are acceptable). Pi5 data-stack paths only: `/ssd-data/infra/docker-compose.yml`, `couchdb/local.d`, `postgres` and `pgbouncer` config (not data), `rustfs` config, `/etc/ssh`, `crontab`, systemd units; Pi5 non-data configs (`Caddyfile`, `traefik/dynamic.yml`, `adguard`, `/etc/wireguard`) are included until A6 moves them, then dropped; VM100 `/opt/apps/*`
compose files and env files, `/etc/systemd/system/homelab-backup*`; VPS `/root/gateway`, `/root/coturn`, `/root/firewall-backup`.
Exclude data volumes and caches.

5.2 Add class `configs` to `schedule.yaml`, `inventory.yaml`, `policies.yaml` (14/8/12), a new restic repo `homelab-backups/configs`,
and a runner **on VM100** that pulls each host's list (read-only, `tar` or `rsync --server --sender` through the forced-command guard
`automation/backup-runner/pi-ssh-guard.sh`), so Pi5 runs no restic and holds no new secret. VPS pull uses a separate read-only key. 

5.3 Post-check: restore one file from the snapshot and compare checksum.

Acceptance: first snapshot listed; test restore passes; Mezon success summary. Rollback: remove class and timer.

## Phase 6: Second off-site target and VM image (B7, B3). Decision needed.

- B7: add a second restic repo (Backblaze B2 or Hetzner Storage Box, roughly 3 to 5 USD per month) and run `restic copy` after
  each successful class. Achieves 3-2-1. Record the choice before implementing.
- B3: vzdump of VM 100 to a **different** disk or host than the Proxmox VM storage. A Proxmox Backup Server on the same host is
  not a backup. Weekly, keep 3.

## Phase 7: Pull model, Pi5 exports nothing it does not have to (B9). Effort 1 to 2 days. Risk medium.

Goal: VM100 is the backup server; Pi5 only serves queries.

7.1 PostgreSQL: create a dedicated read-only role `backup_ro` (`pg_read_all_data`, `CONNECT`, no `SUPERUSER`, no `REPLICATION`) per instance;
add its password to VM100's backup env and to PgBouncer's `auth_file`/direct pg_hba for `10.0.30.0/24` only. Run `pg_dump -Fc` from VM100 over `pg-net`
(`postgres-pg`). `pg_dumpall --globals-only` needs elevated rights: use `--no-role-passwords` or keep a single narrow forced command on Pi5 for globals.
Compare dump sizes and `pg_restore --list` with the current Pi-side export for one week before cutover.

7.2 RustFS: VM100 does **not** currently see the Pi5-local `rustfs` service on
`s3-net`. The live container is attached to Pi5's `s3-net`, `homelab-net`,
`proxy_net` and `edge-http-net`, with only internal `9000/9001` ports and no
host port binding. Before cutover, provide a private, source-restricted S3
endpoint reachable from VM100 and a read-only RustFS access key; verify object
listing, manifest parity and restore parity for one week. Use the S3 API (AWS
CLI/rclone or `mc mirror` to staging, then restic), instead of exporting the
live volume on Pi5. Do not attach VM100 to Pi5's local Docker networks and do
not publish RustFS through Traefik, Rathole or a public domain.

7.3 CouchDB: do not attach the Pi5 CouchDB container to a VM100-visible
network and do not rely on a CouchDB `_security` member for read-only access;
the ACL model cannot enforce that boundary. Use the deployed private GET-only
proxy on `10.10.0.5:15984`, compare the full manifest and restore result from
VM100, then cut over only after the comparison gate passes.

7.4 After a week of matching output, disable the Pi5 `databases` and `rustfs` classes and remove `pi-executor.sh`; delete `runner.env` and the rclone token from Pi5.

Acceptance: `ssh pi 'pgrep -a "restic|rclone|pg_dump"'` empty at backup time; Pi5 load during backup under 1; restore drill (Phase 4) still passes from the new snapshots.
Rollback: re-enable the Pi classes (kept disabled, not deleted, for two weeks).

## Phase 8: Align Pi5 role (A6, informational, no change in this plan)

Candidates to leave Pi5 for VM100 or another node, in order of risk: monitoring stack and Kuma, registry, pgAdmin, LibreSpeed, Semaphore and provisioner;
AdGuard, edge Traefik and Rathole remain on Pi5 by operator decision; exclude them from migrations.
Data-server hardening to decide: NVMe SMART and temperature alerts (probe from VM100), UPS, and PITR. Nightly dumps give a 24 h RPO; for a pure data
server consider pgBackRest with WAL archiving to a VM100 repo host over `pg-net` (decision L2, now P2).

## Order and dependencies

Phase 1 then 2 (including 2.5, which takes check and prune off Pi5) then 3 (alerts need a stable schedule) then 4 (needs the retention proof) then 5; Phase 7 after the restore drill has passed once, so the new pull path can be validated against a proven restore; Phase 6 and 8 after decisions.
First pass (Phases 1 to 5) about 16 hours of work, spread over a week; Phase 7 one to two further days. Re-run `check-backup-health.sh` after each phase.

## Open questions

0. Confirm Pi5 should hold no restic credentials at all after Phase 7.
1. Which external heartbeat service (or none)? 2. Accept `SKIP=builds,artifacts` for GitLab backups? 3. Where can vzdump land
(NAS, USB disk, second Proxmox node)? 4. Cause of the 2026-10-19 reboot.
