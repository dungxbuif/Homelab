---
type: Reference
title: "Homelab Backlog"
description: "Open Homelab work only, verified against the 2026-10-31 live audit and mapped to the IaC rebuild plan phases"
timestamp: 2026-10-31T11:05:44+07:00
---

# Homelab Backlog

Open work only; completed items live in git history and [LOG.md](./LOG.md).
The forward roadmap is the
[Lab IaC and automation rebuild plan](./superpowers/plans/2026-10-31-lab-iac-automation-rebuild.md)
(status: proposed). The **Plan** column maps each item to its phase (P0–P8).
Status values: `open`, `partial`, `blocked`, `decision`.

## P0 Urgent / security

| ID | Item | Acceptance gate | Plan | Status |
|---|---|---|---|---|
| S0 | MikroTik DHCP may still advertise DNS `10.10.0.2` (Orange Pi, now down) | Verify live DHCP DNS; if still `10.10.0.2`, change to `10.10.0.5` with approval and confirm LAN split-DNS. | P0 | open (verify urgently) |
| S1 | Rotate credentials previously exposed in the public GitHub repo history | Public reachable refs audited clean on 2026-10-21; issuer-side rotation of anything previously exposed is still required. | P0 | partial |
| S3 | Rotate the GitLab PAT exposed in a shell error during the 2026-10-31 mirror preflight | Revoke/rotate the PAT, update the mode-`0600` local secret file, verify one authenticated API call. Value is never recorded. | P0 | open |
| S2 | VPS HostSNI edit outage root cause | Guarded edit path exists; live dry-run/smoke still needs an approved hash and operator access. Superseded long-term by catalog-rendered HostSNI. | P3 | partial |
| S4 | VPS hardening | UFW is inactive and no gateway container has a Docker healthcheck (see [VPS gateway audit](./deployments/vps-gateway-audit-2026-10-31.md)); enable firewall with the approved port list and add healthchecks; run authenticated NetBird/RustDesk session tests. | P3 | open |
| R8 | SSH/API key migration | Inventory consumers, move keys to the password-manager boundary, rotate/revoke one at a time, verify each consumer; one `automation` identity across hosts. | P0 | open |
| R13 | Rotate Homelab Mezon notifications into a Swarm secret | Webhook is in 1Password as `Homelab Secret/Mezon - Homelab channel webhook`; live `db-management_mezon_webhook` does not match. Replace via release path, verify sanitized delivery, remove old secret. | P0 | open |

## Backup and DR

The live audit found **no backup timers** on VM100, Pi5 or VM110. The
`databases` class gate passed on 2026-10-31
([backup repair](./deployments/backup-repair-2026-10-31.md)) and Databasus
verifies the six approved service DBs, but recurring schedules for the other
classes are unconfirmed.

| ID | Item | Acceptance gate | Plan | Status |
|---|---|---|---|---|
| B0 | Confirm where GitLab, RustFS, Redis and host-config backups are scheduled | If none, temporarily re-enable the previous runner until P6 assigns one owner per class. | P0 | open |
| B2 | Host config backup schedule | Re-enable/replace the configs class and observe a recurring scheduled run. | P6 | open (scheduler inactive) |
| B3 | VM100 vzdump | Add a separate failure-domain target (PBS/NAS/vzdump to off-host) before the first image backup. | P6 | open (target decision) |
| B4 | Dead-man's switch and alerts | Observe a live scheduled health run with external heartbeat. | P6 | open (scheduler inactive) |
| B5 | Health check false negatives | Capture a fresh lock-free scheduled health run. | P6 | open (scheduler inactive) |
| B8 | Monthly automated restore test | One scheduled restore marker/notification, run as a Semaphore job. | P6 | open (scheduler inactive) |
| B9 | Make Pi5 passive for backups | RustFS/PostgreSQL native pull done; CouchDB native pull and moving the scheduled `databases` class off Pi5 remain. | P6 | partial |
| B12 | Restore GitLab backup schedule after the 2026-10-28 local purge | Fresh off-host GitLab backup, remote snapshot + restore marker, retention set. | P6 | open |
| R4 | Databasus coverage | Re-authorize Drive, then fresh-backup and isolated-restore every in-scope job; classify/enroll `relayhub_v1_staging_20261030`. | P6 | blocked (Drive OAuth 401; admin credential stale) |
| L5 | VM110 `db-ops` as backup/DB-ops worker | Currently runs only db-management Swarm tasks; migrate backup classes one at a time; rebuild-from-zero drill. | P6 | open |

## Platform and runtime

| ID | Item | Acceptance gate | Plan | Status |
|---|---|---|---|---|
| P1 | Swarm cleanup | Remove down node `orangepizero3`; remove `0/0` services `edge_traefik`, `edge_rathole`, `edge_adguardhome`, `relayhub` (bootstrap legacy), `mypocket-web` after owner confirmation. | P2 | open |
| P2 | Docker engine drift | Pi5 28.4.0, VM100 29.8.2, VM110 29.1.3; pin one version and upgrade node by node. | P2 | open |
| P3 | Pi5 edge as code | Standalone `edge-traefik-pi5`, `edge-rathole-pi5` (`rathole:local`), `edge-adguardhome-pi5` (`latest`) into a managed compose with digests. | P3 | open |
| P5 | Retire legacy RelayHub Go | VM100 compose `prod` (relayhub-api/worker/nats/redis) is rollback-only; retire after owner confirms. | P5 | decision |
| R5 | Clean VM100 state | Inventory volumes/runtime/rollback artifacts; move state to the approved host; remove only verified orphans. Disk 66% used. | P5 | open |
| R1 | Audit and normalize Pi5 databases | Owner, host, backup class, retention for each PostgreSQL/CouchDB/Redis/RustFS store. | P5 | open |
| R2 | Move stray databases to Pi5 | One engine at a time with restore checks before cleanup (legacy RelayHub PostgreSQL already retired). | P5 | partial |
| R10 | GitLab/RustFS write-path review | Measure growth/write frequency, classify durable data, decide DB suitability without weakening restore. | P5 | open |
| R11 | Review every sync mechanism | Map LiveSync, CouchLoom changes feed, backups, replication; verify source of truth, delete propagation, auth, rollback. | P5 | open |
| C1 | Pi5 Cloudflared tunnel | Native systemd unit flaps with `Unauthorized: Tunnel not found`; repair token/tunnel or retire. | P3 | blocked (deferred by operator) |

## Image updates

Rule: capture current digest, back up, deploy one service at a time, run
canaries, keep a bounded rollback. Ledger:
[version-upgrade-2026-10-31](./deployments/version-upgrade-2026-10-31.md).

| ID | Service | Remaining gate | Status |
|---|---|---|---|
| U0 | GitLab CE `18.11.11` | Staged path `18.11.14` → `19.2.10` → `19.5.3` after a manageable native backup (B12). | open |
| U1 | n8n + runners `2.46.3` | Authenticated Code-node execution and gold-price/Mezon canary receipts. | partial |
| U5 | Databasus `v3.64.0` | Verify all jobs, latest-success markers, Drive target and failure notifier (see R4); current audit found Drive HTTP 401. | blocked |
| U7 | Semaphore `v2.19.17` | One bounded no-op task receipt. | partial |
| U8 | Family Tree `oven/bun:1-slim` | Pin tag/digest and pass app tests before rollout. | blocked |
| U9 | RelayHub Redis `7.4` | Queue/reconnect and latency receipts. | partial |
| U10 | Backup relay Nginx (3) | Reconcile Diun state with registry; no proven candidate. | blocked |
| U11 | Diun | Fix 15–16 registry failures per scan before trusting its signals. | blocked |
| U12 | Private/local app images | Repair registry visibility; current-vs-candidate digest inventory; drift-free digests (P5 exit). | blocked |

## Automation and documentation

| ID | Item | Acceptance gate | Plan | Status |
|---|---|---|---|---|
| A8 | GitLab CI deploy job with manual approval (Homepage) | Protected variables/environment plus one positive and one no-op live acceptance. | P1 | partial |
| A1 | AI model rollout | Runtime and synthetic gates pass; owner business UAT remains. | — | partial |
| R6 | Homelab documentation organization | Small set of current, self-contained docs; history in git. | — | partial |
| R9 | Keep source code out of the vault | Automated guard for source/build output (LiveSync `docs/**` only). | P1 | partial |

## Standing decisions (not work items)

- Single encrypted Google Drive remote copy; no second off-site target (B7).
- Pi5 stays the DB/data host; VM100 is production compute (L1). No PITR /
  pgBackRest (L2).
- `homelab` CouchDB stays private/admin-only; no public `sync-db` route (E1).
