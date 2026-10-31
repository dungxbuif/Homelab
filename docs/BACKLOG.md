---
type: Reference
title: Homelab Backlog
description: Open Homelab work only, verified against the 2026-10-31 live audit and mapped to the IaC rebuild plan phases
generated:
  by: claude-code/opus-5.5
  at: "2026-10-31T11:05:44+07:00"
stale_after: "2026-11-30T11:05:44+07:00"
---

# Homelab Backlog

Open work only; completed items live in git history and [log.md](./log.md). Backlog confirmed by the owner on 2026-10-31.
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

## Control, standards and docs (added 2026-10-31)

| ID | Item | Acceptance gate | Plan | Status |
|---|---|---|---|---|
| C1 | Adopt hand-made services: 15 Swarm services without a stack, 7 VM100 compose projects | Every running service has a file in `homelab-ops/stacks/`; nightly drift report clean | P0.5 | open |
| C2 | Push local-only images (macocr-proxy, mezonhook, openclaw, k8s-syntax, relayhub-v1, relayhub-admin, couchloom, whiteboard-*, rathole) to GitLab Registry | Services pinned by registry digest | P0.5 | open |
| C3 | Promote GitLab Registry from trial per the [registry decision](./standards/registry.md): storage → RustFS bucket `gitlab-registry` (14 GiB today), metadata DB, GC, cleanup policy; move MyPocket off the Pi5 registry | All digests pull from RustFS-backed registry; bucket backed up + restore test | P4 / P4b | open |
| C4 | Read-only inventory of all databases, users and buckets; adopt with `adopt: true` | Plan shows 0 changes per app ([process](./standards/database-provisioning.md)) | P0.5 / P5 | open |
| C5 | Replace Semaphore `db-provision` and the provisioner with `db_provision` | First new DB created by the CI job, with backup and secret | P1 | open |
| D1 | Repo-side docs per the [project doc standard](./standards/project-documentation.md): fix READMEs that describe other projects (MyPocket, devtool, pocketnode), add `docs/configuration.md` + CHANGELOG to deployed projects, remove lab internals from mac-ocr/mezonhook/k8s-syntax deploy docs | G7 pass for every deployed project | P4 / P5 | open |
| D2 | Whiteboard: reconcile uncommitted changes in `/opt/apps/whiteboard` on VM100 with the `devtool` checkout | Deploy dir clean, deployed revision recorded | P5 | open |
| D3 | k8s-syntax is class `lab` but publicly routed | Route made LAN-only or class changed with gates | P5 | open |
| D4 | Third-party docs: move `n8n-nodes-mezon` into Git; decide BDS leftovers (`bds-app_bds_network`, `bds_prod`) | Repo exists / leftovers retired | P5 | open |
| A1 | Build the automation glue: `hl new`, doc-bot, gate-bot, nightly/weekly reports, issue automation ([flows](./standards/automation-flows.md)) | Homepage completes flows A1–A10 with approvals only | P4b | open |
| A2 | Maintenance flows: unattended security patches, monthly rolling reboot, pinned Docker engine, weekly cleanup | Nightly check `changed=0`; reboot run receipt | P2 | open |
| C6 | One registry for the whole lab: GitLab protection plan G1–G6 (verified backup → VM 120 → registry on RustFS → move all images incl. third-party → delete `registry.dungxbuif.com`) | [GitLab protection plan](./superpowers/plans/2026-10-31-gitlab-protection-and-registry-consolidation.md) exit for G6 | P0.5–P4 | open |
| R0 | Measure the Proxmox host (RAM, CPU, thin pool) to pick the [sizing](./superpowers/plans/2026-10-31-compute-layout-and-sizing.md) row | Sizing row chosen; needs Proxmox read-only access | P0 | blocked (access) |
| R1 | Reclaim unused Docker images: VM100 10.7 GiB, Pi5 49 GiB (images + build cache); `fstrim` VM100 | Space reclaimed, no service touched | P0 | open |
| R2 | Create VM120 gitlab (6 vCPU / 12 GiB / 100 GiB), move GitLab, then VM100 16→12 GiB and VM110 8→12 GiB + scratch disk | Steps R3–R8 of the compute plan | P2 | open |
| R3 | Three Swarm managers (Pi5, VM100, VM110) | `docker node ls` shows 3 reachable managers | P2 | open |
| GP | **GitLab production task**: VMs under OpenTofu, safe migration to VM120, native scheduled backups to Drive that verify themselves and leave no junk ([task](./superpowers/plans/2026-10-31-gitlab-production-task.md)) | T0–T12 done, definition of done met | P0–P2 | open: T4 done (first verified set on Drive, timer still disabled); T3 done; T5 restore drill, timer enable and registry class pending; T0/T1/T6+ blocked on Proxmox access |
| GP1 | Enable `homelab-gitlab-backup.timer` on VM100 (daily 02:00) after the owner agrees | `systemctl is-enabled` = enabled and the next night's set appears and verifies | P0 | decision |
| GP2 | T5: restore the Drive set into an isolated GitLab and run the checklist | Drill passes; RTO and RPO recorded | P0 | open |
| GP3 | Run the freshness check on a second host (needs the Drive config on VM110) | Alert fires when the newest set is older than 26 h | P0 | open |
| GP4 | Back up the GitLab registry directory (restic, weekly), separate from the native set | A registry restore is tested | P0 | open |
| S5 | Confirm `restic-password` and `rclone.conf` from VM100 exist in `Homelab-Recovery`; add a second offline `age` recipient; rename and tag older 1Password items | [Secrets standard](./standards/secrets-1password.md) section 8 closed | P0 | open |
| VB1 | **VM100 has no scheduled backup.** All 9 legacy `homelab-backup-*` timers are disabled; the last successful runs were 2026-10-21 and 2026-10-22. VM100 holds its own state that is not on Pi5: `/opt/apps/{n8n 571M, openclaw 841M, family-tree 804M, macocr-proxy 721M, couchloom 382M, netbird 33M, whiteboard 55M}` and volumes (`netbird_netbird_data` 59M, `couchloom_pgvector_data` 108M, one unnamed 585M). First inventory what each holds (n8n encryption key, NetBird server data and OpenClaw state are the likely critical ones; contents unverified), then add an encrypted app-state class using the same age + Drive tooling | Inventory recorded in each project doc; nightly class verified; restore of one app tested | P0 | parked: outside the GitLab task |
| VB2 | `/opt/apps/homelab-backup` is 3.8 GB of legacy runner output (rollback and release directories, old restore drills) | Review the list, delete what is obsolete with approval, keep what the disabled timers still need | P0 | parked: outside the GitLab task |
