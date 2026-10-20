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
| N1 | Detach `homelab-net` from `postgres` | Shared flat network exposes Postgres to every service on it | Script `pgnet-step-d-detach.sh` (backup compose, `docker network disconnect`, verify clients are `10.0.30.x`, five sites 200). pgbouncer, whiteboard and gitlab already use `pg-net` | ready |
| N2 | Flush old pgbouncer server connections | About 12 connections (mypocket, netbird, relayhub) still ride `homelab-net` | Recreate pgbouncer from compose, or let N1 drop them once | open |
| N3 | relayhub reaches PgBouncer via LAN `10.10.0.5:5432` | Host port stays published only for this client | Put relayhub on an overlay (or `pg-net`), then stop publishing 5432 | open |
| N4 | Bind remaining host-published datastore ports | Datastores should not listen on all interfaces | `127.0.0.1` or LAN-only binds in compose; verify from outside | open |
| N5 | Keep `homelab-net` only where `redis-prod` is needed | GitLab still needs it for Redis | Dedicated `redis-net`, then retire `homelab-net` | open |
| N6 | Compose drift on Pi5 | Live `postgres` was attached to networks the compose file did not list | Reconcile `/ssd-data/infra/docker-compose.yml` against live; make Ansible/CI the only writer | open |

## P1 Backup (see assessment below)

| ID | Item | Why | How / verify | Status |
|---|---|---|---|---|
| B1 | Remote Drive restore acceptance | Backups are unproven until a full restore works | Quarterly drill: restore Postgres, CouchDB, GitLab, RustFS to scratch and compare | open |
| B2 | Backup of host configs | Compose files, Traefik, Caddy, `/etc`, secrets are not a backup class | Add `configs` class (encrypted) | open |
| B3 | VM100 vzdump | VM-level recovery has no image | vzdump to a second target; or Proxmox Backup Server | open |
| B4 | Dead-man's switch and alerts | A silent scheduler failure goes unnoticed | Healthchecks-style ping per class plus Mezon alert | open |
| B5 | Health check false negatives | 2026-10-19 health failed only because retention held the lock for 45 minutes | Make health lock-aware; move retention away from the GitLab window | open |
| B6 | VM100 disk pressure | On 2026-10-18 only 105 MB was free: GitLab backup and retention failed | Alert at 85 percent, schedule `docker image prune`, size the disk | open |
| B7 | Second off-site target | Google Drive is the only remote copy | Add a second restic repo (B2, Hetzner box or LAN NAS) for 3-2-1 | decision |
| B8 | Monthly automated restore test | Replaces manual checks | CI or systemd job restoring latest snapshot and running a query | open |

## P2 Exposure and routing

| ID | Item | Why | How / verify | Status |
|---|---|---|---|---|
| E1 | `homelab` CouchDB (5.9 GB, admin-only) | LiveSync copy of this repo; not exposed on `sync-db` | If remote sync is needed, create a non-admin `_security` member and add `PathPrefix(/homelab)` to the `sync-db` rule; review size or compact | decision |
| E2 | Catalog vs live drift | `catalog.yml` marked `couchdb`/`pgadmin` as `exposure: lan`; live file did not | Generate Pi5 `dynamic.yml` from `automation/routes/catalog.yml` | open |
| E3 | `couchdb.` and `sync-db.` share a backend with split routers | Hand edit lives only on Pi5 | Move the router split into the catalog | open |

## P2 Automation

| ID | Item | Why | How / verify | Status |
|---|---|---|---|---|
| A1 | GitLab CI deploy job with manual approval | Approval enforced by GitLab, not by Semaphore Community | Forced-command SSH key, job per stack | open |
| A2 | Nightly drift job | Catch live-vs-repo drift | Compare `docker service ls` and published ports with the repo, report to Mezon | open |
| A3 | Image updates | No pinned digests | Renovate or Diun (notify only), `order: start-first`, healthchecks | open |
| A4 | Break-glass path | GitLab runs on the infrastructure it deploys | Document workstation SSH recovery | open |
| A5 | Trim Semaphore | Stop expanding it | Keep only read-only host-audit and backup-health templates | open |
| A6 | Move monitoring and control plane off Pi5 | Failure domains overlap | Place on VM100 or a separate node | open |

## P3 Later

| ID | Item | Status |
|---|---|---|
| L1 | Decide on a data VM after measuring Proxmox capacity | decision |
| L2 | pgBackRest only if PITR is required | decision |
| L3 | Postgres collation-version warning (`ALTER DATABASE ... REFRESH COLLATION VERSION`, then reindex) | open |
| L4 | Decommission legacy Pi `/ssd-data/backup/simple-backup.sh` after B1 passes | open |

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
