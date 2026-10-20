---
type: Plan
title: "Backup Hardening Plan (2026-10-20)"
description: "Detailed phased plan to fix backup alerting, disk pressure, lock overlap, retention proof, restore drills and config backup"
timestamp: 2026-10-20T00:00:00+07:00
---

# Backup Hardening Plan, 2026-10-20

Backlog items: B1 to B8 in [BACKLOG.md](../BACKLOG.md). Runbook: [backup-restore.md](../runbooks/backup-restore.md).
Runner code: `automation/backup-runner/`, `backup/scripts/`. Status: **plan, nothing applied**.

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
| Docker on VM100 is unhealthy | `docker system df` fails: `rw layer snapshot not found for container 1711725e...`; VM rebooted about 2026-10-19 16:30 local, cause unknown |
| Only Google Drive holds remote copies | Three restic repos under `homelab-backups/{databases,gitlab,rustfs}`; no second target, no restore drill, no host-config class, no VM image |

Answers to the three questions raised: (1) spacing the jobs did not prevent the 2026-10-18 failure because the cause was
free space, not overlap; the overlap problem is separate (section 3). (2) Yes, retention for backed-up databases is
configured and ran successfully, but its effect is **unproven**: no snapshot count per repo has been compared with the policy
(Phase 1.4). (3) This document is that plan.

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

Acceptance: top consumers documented; `docker system df` works; `/` below 70 percent after cleanup; snapshot counts match policy;
health reports the new thresholds. Rollback: remove the drop-ins and timer; no data deleted except pruned images and journals.

## Phase 2: Schedule and health without false alarms (B5). Effort 2 h. Risk low to medium.

Problem: the nightly lock chain is serial and long, and health runs inside it.

2.1 **Retention cadence.** Replace the nightly 4.5 h full check with: nightly `restic check` (structure only, minutes) plus
`forget --prune` after a successful night; a weekly (Sunday 08:00) `restic check --read-data-subset=10%`.
Files: `automation/backup-runner/run-retention.sh`, `backup/scripts/verify-retention.sh`, `systemd/homelab-backup-retention.timer`,
new `homelab-backup-verify-weekly.timer`.

2.2 **New order (local time).** 01:00 databases, 01:30 database-instances, 02:00 RustFS (40 min), 02:30 GitLab (3 h 20 min, ends
about 06:00), 06:30 retention light (about 20 min), 08:00 health, Sunday 09:00 deep verify. Update `schedule.yaml` and the four timers
(`homelab-backup-*.timer`), then `systemctl daemon-reload`.

2.3 **Lock-aware health.** In `check-backup-health.sh`, if the global lock is held or a backup unit is `activating`, print
`state=running runtime=Ns` and exit 0 unless runtime exceeds a class limit (databases 30 min, GitLab 5 h, RustFS 90 min,
retention 90 min, deep verify 8 h). Only stale markers (older than 26 h) and failed units fail.

2.4 **GitLab wall time.** Investigate why the native backup takes 3 h 20 min for 8.2 GB (compression, `STRATEGY=copy`, skipped
content `SKIP=builds,artifacts` if acceptable). Record before changing.

Acceptance: three consecutive nights with health exit 0 and no overlap in `journalctl`; a forced stale marker still turns it red.
Rollback: restore the previous timer files from git and reload systemd.

## Phase 3: Dead-man's switch (B4). Effort 3 h. Risk low.

3.1 Use the Uptime Kuma instance already on Pi5 (`/ssd-data/infra/kuma-data`): create one **push monitor** per class
(databases, database-instances, gitlab, rustfs, retention) with a 26 h heartbeat (retention 8 days for the weekly deep verify) and
a Mezon notification channel. Each class pings its push URL at the end of `run-class.sh` only after the success marker is written;
URLs live in the existing secret env file, never in git.

3.2 Because Kuma runs on Pi5 (the thing being protected), add one external heartbeat: a single daily `curl` from VM100 to a
free external check service after health passes, with its own email or push channel. This covers Pi5 or LAN loss.

3.3 Add a Mezon message on **every** failed class (exists) and a daily one-line success summary from health.

Acceptance: disable one timer for a day in a test window; both Kuma and the external check alert. Rollback: remove the `curl` lines.

## Phase 4: Restore drill, then automate (B1, B8). Effort 4 h first run, 2 h to automate. Risk low (scratch only).

4.1 Scratch target: a throwaway Postgres 16 (pgvector image used in prod) and CouchDB container on VM100 with no published ports
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

5.1 Inventory to cover (encrypted by restic, so secrets are acceptable): Pi5 `/ssd-data/infra/docker-compose.yml`, `Caddyfile`,
`traefik/dynamic.yml`, `couchdb/local.d`, `adguard`, `/etc/wireguard`, `/etc/ssh`, `crontab`, systemd units; VM100 `/opt/apps/*`
compose files and env files, `/etc/systemd/system/homelab-backup*`; VPS `/root/gateway`, `/root/coturn`, `/root/firewall-backup`.
Exclude data volumes and caches.

5.2 Add class `configs` to `schedule.yaml`, `inventory.yaml`, `policies.yaml` (14/8/12), a new restic repo `homelab-backups/configs`,
and a runner that tars each host's list through the existing forced-command SSH guard (`automation/backup-runner/pi-ssh-guard.sh`).
VPS pull uses a separate read-only key. 

5.3 Post-check: restore one file from the snapshot and compare checksum.

Acceptance: first snapshot listed; test restore passes; Mezon success summary. Rollback: remove class and timer.

## Phase 6: Second off-site target and VM image (B7, B3). Decision needed.

- B7: add a second restic repo (Backblaze B2 or Hetzner Storage Box, roughly 3 to 5 USD per month) and run `restic copy` after
  each successful class. Achieves 3-2-1. Record the choice before implementing.
- B3: vzdump of VM 100 to a **different** disk or host than the Proxmox VM storage. A Proxmox Backup Server on the same host is
  not a backup. Weekly, keep 3.

## Order and dependencies

Phase 1 then 2 then 3 (alerts need stable schedule) then 4 (needs working retention proof) then 5; Phase 6 after a decision.
Total first pass about 14 hours of work, spread over a week. Re-run `check-backup-health.sh` after each phase.

## Open questions

1. Which external heartbeat service (or none)? 2. Accept `SKIP=builds,artifacts` for GitLab backups? 3. Where can vzdump land
(NAS, USB disk, second Proxmox node)? 4. Cause of the 2026-10-19 reboot.
