---
type: Deployment
title: "DB-management production gate matrix"
description: "Evidence matrix for deployment, backup, restore, Databasus, rollback and legacy retirement"
timestamp: 2026-10-26T03:12:00+07:00
---

# DB-management production gate matrix

This is an evidence checklist, not a blanket production-ready declaration.
The current release path and native Drive backup path are live; the remaining
gates below must be closed independently.

## Evidence matrix

| Gate | Current evidence | Status | Required proof to close |
| --- | --- | --- | --- |
| GitLab provenance | Pipeline `537`, deploy job `1668`, immutable app/ops SHAs, successful receipt | passed | Keep the protected deploy approval `false` outside an approved release |
| Swarm convergence | After storage recovery, `db-ops` and `vm100-prod` are Ready; API, worker, web, CloudBeaver and Databasus are `1/1` | passed for current runtime | Keep observing after GitLab/VM recovery |
| Private routing | API readiness, Redis monitor status/metrics, CloudBeaver status and Databasus health returned HTTP `200` | passed for current runtime | Repeat after the next image or network change |
| Proxmox storage safety | Thin pool was extended without deleting disks/snapshots; `local-lvm` is now approximately 96% used with 13.7 GiB free | open | Add capacity headroom and prove an autoextend/alert policy before calling the base fully reliable |
| Companion stack provenance | Source commit `f52a1dd` is pushed to the ops branch and the live stack contains the CloudBeaver/Databasus PostgreSQL network changes; the apply was a controlled manager-side stack update, not a protected CI deployment | partial | Record the approved CI/ops deployment receipt for this companion-stack revision |
| Native Drive backup | Four fresh PostgreSQL/CouchDB source jobs succeeded with local markers, remote receipt and verified upload metadata | passed for backup path | Continue scheduled observation and retain secret-free evidence |
| Local staging cleanup | Completed verified staging is removed; failed/stale evidence is preserved | passed for current policy | Verify retention/prune behavior over one seven-day cycle |
| PostgreSQL restore | All fresh PostgreSQL artifacts passed isolated restore: production `13/13` dumps and Couchloom `2/2` dumps on PostgreSQL `17.11` scratch | passed | Repeat after backup/major-version changes |
| CouchDB restore | Both fresh CouchDB artifacts passed isolated restore: Obsidian `49,229/49,229` and Homelab `1,519,950/1,519,950` documents with security metadata | passed | Repeat after adapter/schema changes |
| CloudBeaver | Expired configuration was repaired; anonymous access is disabled, the local admin authenticates as `ADMINISTRATOR`, and a private PostgreSQL `testConnection` passed. Credentials were not saved to the workspace | passed | Recheck after CloudBeaver image or network changes |
| Databasus | v3.60.0 task and health endpoint are healthy, the task resolves PostgreSQL over `pg-net`, and official CLI lists a bootstrap administrator; no authenticated token, workspace, provider, retention or restore acceptance | open | Operator supplies/rotates the admin credential through the supported CLI/UI, then records provider, retention, backup and isolated restore evidence |
| Rollback | Pi receipt `db-management-release-uycghr05` for pipeline `537` contains the previous API/worker/web image set and current services match the requested set; no maintenance-window exercise is recorded | open | Perform a controlled rollback to the previous receipt, verify readiness, then return to the current release |
| Legacy retirement | Pi legacy cron and VM100 db backup timers are disabled, but authenticated Semaphore inventory still shows the Manager-approved `backup-client-release` template with recent tasks; VM100 relay containers remain active dependencies | open | Separate the old DB scheduler from still-used relay/control-plane components, migrate or explicitly retain each consumer, obtain approval, then retire one owner at a time with rollback evidence |

## Isolated restore evidence — 2026-10-26

These were disposable, loopback-only restore exercises. They did not target a
production database and the temporary containers were removed after the checks.

- PostgreSQL source run `0615effb-947c-4a33-bc49-fc6ef385fdae` was downloaded
  from Drive and its `14/14` artifact checksums were verified before restore.
  The PostgreSQL 17.11 image was pinned to
  `pgvector/pgvector@sha256:cf134a767f474095eeba57e0117be8e568e011a63f33fbf252f14c9b760f8e6f`.
  All 13 database dumps restored into disposable `restore_*` databases; the
  `globals.sql` roles/passwords were intentionally not applied.
- CouchDB source run `f2fe3ca8-afdb-4ca9-81a2-b875c2bc7f12` restored the
  `obsidian_vault` artifact into a disposable CouchDB 3.3.3 target. The
  source and target both contained `49,229` documents; security metadata was
  applied and the source had no attachment documents. The target was removed
  after verification.
- Couchloom PostgreSQL run `7b96b3d1-8042-492c-9279-845233a0a8e9` passed
  checksum verification and restored both dumps on PostgreSQL 17.11; the
  `couchloom` database contained 15 user tables and the intentionally included
  empty `postgres` dump restored as a valid database.
- CouchDB Homelab run `c5fce5b0-50fe-43af-83da-7eee0949985a` passed checksum
  verification and restored `1,519,950/1,519,950` documents with matching
  security metadata. The source contained zero attachment documents. The
  target and all downloaded scratch artifacts were removed after verification.

## CloudBeaver functional and private-session probe — 2026-10-26 03:10 ICT

- The previous `/status` probe returned `200` while CloudBeaver GraphQL
  returned `Server configuration time has expired`. The manager forced a
  restart of only `db-management_cloudbeaver`; its workspace volume and image
  digest were preserved.
- After restart, the unauthenticated GraphQL schema query at `/api/gql`
  returned `200` with a `Query` type. The ops verifier and container
  healthcheck now use this bounded schema probe, so the expired configuration
  state cannot be reported healthy by `/status` alone.
- The local-provider login using the mounted secret returned `SUCCESS`; the
  session reported `isAnonymous=false` and `authRole=ADMINISTRATOR`, with
  anonymous access disabled in `serverConfig`.
- A read-only `testConnection` request through that private session reached
  PostgreSQL production over `pg-net` and returned a PostgreSQL 16.14 server
  version. The connection was not saved, and no credential value was recorded.
- The same GraphQL healthcheck was applied to the live Swarm service from the
  manager after correcting the Docker `CMD-SHELL` wrapping. VM110 reports the
  CloudBeaver task `healthy`, the image digest is unchanged, and the public
  `/api/gql` schema probe passes.

## Live gate recheck — 2026-10-26 02:54 ICT

- `db-management.dungxbuif.com/health/ready`,
  `cloudbeaver.dungxbuif.com/status`, and
  `databasus.dungxbuif.com/api/v1/system/health` each returned HTTP `200`.
- The live CloudBeaver local-provider probe used the mounted admin secret with
  the configured local admin and returned `SUCCESS`; no secret value was
  recorded or changed.
- The CloudBeaver task now joins `pg-net`; DNS from the task resolves
  `postgres` to the Pi5 PostgreSQL endpoint. The saved-connection list remains
  empty by design because the smoke did not persist production credentials.
- The Databasus task also joins `pg-net` and resolves the same PostgreSQL
  endpoint; its provider is not configured or authenticated yet.
- Databasus `v3.60.0` reported a healthy internal database and disk state. Its
  supported admin inventory command found one active bootstrap administrator;
  the password was not printed, reset or stored by this check.
- The local 1Password CLI session was signed out, so no credential retrieval or
  password rotation was attempted. The Databasus gate therefore remains open.
- The Pi5 release state records pipeline `537` as the current successful
  release, with previous image digests for all three mutable components. No
  rollback was executed because it is a live service mutation requiring an
  approved maintenance window.

## Live gate recheck — 2026-10-26 03:12 ICT

- The final companion-stack apply converged API, worker, web, CloudBeaver and
  Databasus at `1/1`; both CloudBeaver and Databasus tasks are healthy and
  resolve `postgres` to `10.0.30.12` through `pg-net`.
- The bounded release verifier returned `release=passed` with API,
  CloudBeaver and Databasus route checks passed. Fresh HTTPS probes returned
  HTTP `200` for API readiness, CloudBeaver status/GraphQL and Databasus
  health.
- The ops contract suite passed `189` tests. CloudBeaver private login and
  non-persisted PostgreSQL `testConnection` still pass after the Databasus
  network update.
- The app CI source now pins the ops contract to
  `0763f2ba8b92a764f186333b1d8f6962ce26d756`. Pipeline
  [#569](https://gitlab.dungxbuif.com/dungxbuif/db-management/-/pipelines/569)
  passed `quality` and `ops-contract` for app commit
  `bb0793b94ce450f7da92df87d39421fb831b6b5b`; it did not build or
  deploy production.
- This recheck does not close Databasus authenticated provider/retention/
  restore, controlled rollback, legacy retirement, or companion-stack
  protected-CI provenance.

## Read-only legacy inventory — 2026-10-26

- Pi5 `crontab` contains the old `simple-backup.sh` entry only as a disabled
  comment. Its active timers observed in this check were unrelated OS timers.
- VM110 has the db-management services and unrelated OS package timers; no
  Restic/rclone backup container or backup timer was observed.
- VM100 has three active `homelab-backup-db-ops-*` Nginx relay containers for
  PostgreSQL, Couchloom PostgreSQL, and CouchDB. They are transport
  dependencies used by the current source connections, not proof that the old
  scheduler is still active; they must be retained or migrated as a separate
  network-ownership decision.
- Pi5 still runs the Semaphore UI and executor runner. The repository still
  contains legacy Restic/rclone scripts and Semaphore backup templates, so the
  runtime observation is insufficient to prove that every consumer is gone.
- Pi5 also runs the `couchdb-backup-proxy` compose service. Its consumers and
  relation to the new direct CouchDB adapter are not yet authenticated and
  proven, so it is not deleted.
- VM100 had three stale failed states from the disabled legacy path:
  `homelab-backup@databases.service` failed on an unsafe rclone work directory,
  `homelab-backup@retention.service` failed its old retention prerequisites,
  and `homelab-backup-health.service` reported missing legacy markers. All
  related timers were already disabled; this was not an active db-management
  failure.
- No legacy service or script is deleted by this note. Retirement requires an
  authenticated inventory and explicit approval.

### Authenticated Semaphore inventory — 2026-10-26 02:55 ICT

- The private API login succeeded without exposing the session cookie. Project 2
  (`Homelab Audit`) contains only read-only Pi5/VM100/backup-health templates.
- Project 1 (`Homelab Control Plane`) contains read-only audits, database
  provisioning, source smoke, Homepage release, and the Manager-approved
  `backup-client-release` template (template `7`). The latter imports the
  reviewed Ansible backup-client release playbook and is not the native
  db-management worker.
- Recent Project 1 task IDs `146` and `144` for template `7` completed
  successfully on 2026-10-20; earlier task IDs `143`, `64`, `63`, `62`, `61`,
  and `60` recorded errors. Project 2's latest read-only audit was task `140`.
- This proves the old scheduler is not active, but it also proves Semaphore is
  still an active control-plane consumer. Deleting its templates, release
  playbooks or shared relay dependencies now would be an unreviewed migration,
  so no deletion was performed.

## Safe operating boundary

The db-management worker has no restore HTTP route and must not be pointed at a
production restore target. Restore exercises are separately authorized,
isolated operator actions. Databasus is not treated as a provider API until its
versioned authenticated workflow is configured and independently evidenced.

## CI availability recheck — 2026-10-26

- The db-management services remain `1/1` on the Pi5 Swarm manager; this check
  did not mutate or redeploy them.
- GitLab's `gitlab_gitlab` service is constrained to `vm100-prod` (`10.10.0.31`).
  Proxmox reports VM100 `running` (`vmid 100`, `k8s-cp-1`), but the Swarm node is
  `Down` with `heartbeat failure`, the guest agent is unavailable, and the VM
  does not answer ICMP/SSH. The GitLab HTTPS endpoint returns `502`; SSH `:2222`
  resets after TCP connect.
- The security fix commit `d20b3da` is present locally but is not pushed or
  deployed. It pins Docker CLI `29.9.2` (verified locally to contain Go
  `1.26.10`) and Trivy `0.76.1` after pipeline `#579` still reported the
  vulnerable Docker CLI `29.9.1` binary. The next proof is a successful push and
  protected CI rerun after VM100/GitLab recovery.
- VM100 also hosts GitLab and other services; its controlled power-cycle result
  is recorded in the runtime outage recheck below and did not restore reachability.

## Runtime outage recheck — 2026-10-26 04:16 ICT

- Proxmox reports VM110 (`db-ops`, vmid `110`) as `running`, but its guest has
  no ICMP or SSH response. The Swarm manager reports `db-ops Down`; the API,
  worker, web, CloudBeaver and Databasus tasks are pending because no eligible
  node is available, and the public LAN routes return `502`.
- The Proxmox QEMU guest agent is unavailable. A graceful Proxmox `reboot` task
  and then an ACPI `shutdown` task were issued for VM110; neither changed its
  uptime or restored networking. A controlled QEMU `reset` task also completed
  successfully, but VM110 remained unreachable and Pi5 ARP stayed incomplete.
- A controlled hard power-cycle was then performed for VM110 and VM100 using
  Proxmox `stop` followed by `start`. Both VMs remain `running` at Proxmox but
  their guest IPs still do not answer, and GitLab/db-management remain HTTP
  `502`. No volume deletion or stack redeploy was performed.
- Proxmox now reports `qmpstatus=io-error` for both VMs. The `local-lvm` thin
  pool is `100%` used with `0` bytes available; its inventory includes the
  200-GiB VM100 disk, 80-GiB VM110 disk, the 20-GiB base template and a VM100
  rollback snapshot named `pre-docker-ce-20261014`. Snapshot removal or any
  other storage deletion is intentionally not performed without approval.
- This supersedes the earlier `1/1` live observation as current runtime state;
  the earlier backup/restore evidence remains valid historical evidence, but no
  new backup or restore claim is made during this outage.

## Runtime recovery recheck — 2026-10-26 07:56 ICT

- Proxmox now reports VM100 and VM110 as `running` with QEMU `qmpstatus=running`.
  Swarm reports `vm100-prod` and `db-ops` as `Ready`; Orange Pi remains down.
- The db-management API readiness route returned HTTP `200`. Redis monitor
  status and metrics returned HTTP `200`; this confirms observation only and
  does not add Redis to backup ownership.
- All five db-management services (API, worker, web, CloudBeaver and
  Databasus) are `1/1`. CloudBeaver status and Databasus health returned HTTP
  `200`.
- The recovery action extended the Proxmox thin pool with existing free
  volume-group space and then restarted the affected VMs. No VM disk, backup
  evidence or VM100 rollback snapshot was deleted.
- `local-lvm` now has approximately 13.7 GiB free and is about 96% used. The
  thin allocation remains overcommitted and automatic thin-pool growth has not
  been proven, so storage safety remains an open gate.
- GitLab remains a separate open incident: `gitlab_gitlab` is still `0/1` and
  its HTTPS API returns `502`. No new GitLab pipeline or push is claimed by
  this recovery recheck.

