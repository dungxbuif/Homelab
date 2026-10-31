## 2026-10-31

### VM120 created, VM110 imported and resized

**Update** — With the owner's approval of the migration chain: removed an unused 9.2 GB image on VM100, imported VM110 into OpenTofu with a zero-diff plan, resized VM110 from 8 to 4 GiB (db-management came back 5 of 5), and created VM120 for GitLab (8 GiB, 100 GiB, `10.10.0.33`). Details and the state layout are in the [GitLab production task](/docs/superpowers/plans/2026-10-31-gitlab-production-task.md) section 9a. GitLab itself has not been moved.

### Proxmox host measured, `pve.nccsoft.office` removed

**Update** — With the existing API token (GET only) the Proxmox host measured 31.3 GiB RAM (24.9 in use) and 75 GiB free in the thin pool, so the VM120 sizing was reduced and a resize sequence added ([compute plan](/docs/superpowers/plans/2026-10-31-compute-layout-and-sizing.md)). Read-only `tofu plan` runs showed that the VM100 and VM110 modules are not zero-diff yet. The disk audit found that VM100's space is mostly container images, not data.

**Deletion** — The hostname `pve.nccsoft.office` was removed from the credential template and tooling; the endpoint is the short name `pve`, which the node certificate already lists. The certificate's own common name still carries the old name until the node certificate is regenerated, which was not done.

### VM100 backup coverage audit

**Update** — A read-only audit of VM100 found that all 9 legacy backup timers are disabled and the last successful runs were on 2026-10-21 and 2026-10-22; only the new GitLab set from today exists. VM100 holds about 4 GB of its own application state that no backup covers. This corrects an earlier assumption (see [decisions](/docs/decisions.md)). Backlog items VB1 and VB2 track it.

### First verified GitLab backup on Drive

**Creation** — Created the human-only 1Password vault `Homelab-Recovery` and the item `backup - gitlab - age private key`, written through the CLI without printing the key. Installed `age` on VM100 and deployed the backup tooling with Ansible (check mode first); the timer stays disabled. The first real run produced the set `20261031T062156Z` (455 MB, 38 repositories): uploaded, checksum-verified, and decrypted with the 1Password key. The run exposed one bug (`RuntimeMaxSec` ignored for oneshot units), fixed and redeployed. See the [GitLab production task](/docs/superpowers/plans/2026-10-31-gitlab-production-task.md) section 9.

### GitLab backup tooling and VM120 module written

**Creation** — In `homelab-ops` (branch `feat/gitlab-production`, commit `0c94b8b`): a hardened GitLab backup runner with encryption, verified Drive upload and cleanup on every failed exit, a retention and freshness tool, a plan policy that rejects VM delete or replace and disk shrink, an OpenTofu module for VM120, systemd units and a deploy playbook. See [implementation status](/docs/superpowers/plans/2026-10-31-gitlab-production-task.md). Nothing was applied or deployed.

### GitLab production task and stale backup removed

**Update** — Wrote the [GitLab production task](/docs/superpowers/plans/2026-10-31-gitlab-production-task.md): all VMs under OpenTofu, safe migration to a dedicated VM, native scheduled backups to Google Drive, and failure handling that leaves no junk. The task's audit found that GitLab's real data is small (git 463 MiB, artifacts 59 MiB) while the registry is 14 GiB.

**Deletion** — With the owner's approval, removed the stale 14.3 GB `registry.tar.gz` left in `/opt/apps/gitlab/data/backups/` by the backup stopped on 2026-10-30. VM100 disk went from 66% to 59% used. The live registry was not touched because running services pull images from it.

### IaC plan, vault cleanup, standards and OKF v0.2

**Update** — Live read-only audit of Pi5, VM100 and VM110. The new
[IaC automation rebuild plan](/docs/superpowers/plans/2026-10-31-lab-iac-automation-rebuild.md)
replaces every earlier automation plan: GitLab CI is the only control plane and Semaphore
is retired in P1. Records dated before 2026-10-31 were removed from the working tree (they
remain in git), and the current-state docs were rewritten from the audit with SVG diagrams.

**Creation** — Standards: [app delivery gates](/docs/standards/app-delivery-gates.md),
[project documentation](/docs/standards/project-documentation.md),
[database provisioning](/docs/standards/database-provisioning.md) and
[registry decision](/docs/standards/registry.md). Per-project internal docs now live in
[docs/projects](/docs/projects/index.md).

**Update** — The vault now follows OKF v0.2: `generated`/`stale_after`/`status` frontmatter,
lowercase `index.md`/`log.md` reserved files, and the standing decisions moved to
[decisions.md](/docs/decisions.md).

### Databasus backup/restore audit: gate not passed

- The live audit confirmed the Databasus Swarm service is healthy at `v3.64.0`
  (`1/1`), the Pi5 verification agent is active, and the service/health
  endpoints return HTTP `200` from the LAN route.
- The backup gate is not currently passing: Databasus receives Google Drive
  HTTP `401 Invalid Credentials` while finding/creating `databasus_backups`.
  The failure began at `2026-10-30T19:51:02Z` and affected the six manual
  post-upgrade backup attempts. A native worker receipt cannot substitute for
  Databasus evidence.
- The live PostgreSQL catalog contains 16 non-template databases. Databasus
  documents 15 jobs; `relayhub_v1_staging_20261030` has no documented job and
  needs an explicit staging/enrollment decision.
- The 1Password Databasus admin password currently fails authentication. No
  admin reset, volume replacement, or destructive cleanup was performed.
  Full evidence and the close-out sequence are in
  [`databasus-audit-2026-10-31.md`](./deployments/databasus-audit-2026-10-31.md).

### GitLab Redis/API root-cause repair

- The GitLab API 500 was traced to Rails `Redis::CannotConnectError` while
  updating Personal Access Token last-used state. The exact failure was DNS
  resolution of `redis-prod:6379/2`, not a GitLab image or PAT-scope problem.
- Pi5 `redis-prod` had been recreated from the base Compose file and retained
  only `redis-prod_default`; the current GitLab task uses the selective
  `gitlab-net` overlay. The running Redis container was attached to
  `gitlab-net` with alias `redis-prod`, and the secret-free Pi5 override was
  updated so the attachment survives the next controlled recreate.
- Post-repair evidence: Redis resolved as `10.0.5.31`, authenticated DB2
  `PONG`, GitLab internal health/readiness `200`, and public unauthenticated API
  `401`. No Redis data or image was removed. Full evidence is in
  [the dated repair record](./deployments/gitlab-redis-network-repair-2026-10-31.md).
- The PAT used in the failed preflight was exposed in a shell error. Its value
  is not recorded; revoke/rotate it before any GitLab project creation or push.

### GitLab project mirror wave

- Created 31 private GitLab projects under `dungxbuif` for the Git repositories
  that did not already have a GitLab origin. The four existing GitLab origins
  (`NoteVault`, `db-management`, `homelab-ops`, `homepage`) were verified;
  `db-management` was fast-forwarded to its local `main` because the remote
  was one commit behind.
- Added a second `gitlab` SSH remote to the other 31 repositories and pushed
  each current branch without changing local upstream tracking. Remote heads
  matched local heads for all normal mirrors. `RelayHub` and `homelab-ops`
  retained their pre-existing uncommitted work and did not push it.
- `MyPocket` was the only exception: its local shallow clone referenced a
  missing parent that could not be recovered from GitHub, so a one-commit
  GitLab snapshot was built from the exact local tree and force-with-lease
  replaced the initial incomplete branch. The branch protection was restored
  after the controlled update; the local working tree remains unchanged.
- The 11 non-Git directories were not initialized. Complete project URL,
  remote, branch, dirty-state and verification mapping is in
  [`PROJECTS.md`](./PROJECTS.md).

### Controlled Docker image upgrade ledger

- Started the per-service upgrade runbook with explicit old-image/digest,
  backup, smoke-test, and rollback fields. No image update is considered
  complete until its row in [the upgrade ledger](./deployments/version-upgrade-2026-10-31.md)
  has fresh evidence. The first stateless wave is applied; n8n and its
  external-runner pair are now version-matched, with only authenticated
  Code-node execution left as a follow-up smoke item. The fresh stateful
  backup retry exported locally after a Pi executor runtime-path repair, but
  remote upload failed; no stateful image has been changed. n8n was subsequently matched to its
  `2.46.3` external runners using a GHCR image and a fresh local PostgreSQL
  dump. Alertmanager, VictoriaMetrics,
  and PostgreSQL exporter were then upgraded individually; the exporter also
  required URL-encoding its existing DSN password so `pg_up` returned `1`.
  The database backup export initially hit Drive `invalid_client`; the
  retained OAuth config was then mapped to a newly created
  `homelab-backups/databases` Restic repository and the complete run uploaded
  successfully. VM100 passed the restore drill plus engine-level PostgreSQL
  (`n8n`, `SELECT 1`) and CouchDB (`obsidian_vault`, `49341` docs) checks, so
  the shared `databases` gate is now accepted. Redis still needs its own
  RDB/AOF restore procedure, and RustFS/CouchDB/PostgreSQL still need
  service-specific smoke checks before their image changes. NetBird server `0.82.0`
  and dashboard `v2.96.0` were then upgraded as a backed-up pair; the first
  dashboard attempt used the wrong GHCR prefix and auto-rolled back before the
  correct Docker Hub reference passed public/API smoke.
  Semaphore `v2.19.17` was then upgraded with a validated SQLite archive; its
  private executor was refreshed without changing its image and reconnected
  successfully.
  CloudBeaver `26.2.3` was then upgraded with a validated workspace archive.
  Its first Swarm attempt rolled back because the new image no longer shipped
  `curl` while the old healthcheck required it; the source and live service
  were corrected to a Bash TCP healthcheck, after which the service became
  healthy and its public status endpoint returned HTTP 200.
  PgBouncer was then pinned to the tested `latest` repository digest and
  upgraded to PgBouncer `1.26.1`; Compose hit a fixed-name/external-network
  recreate problem, so the old container was retained under a rollback name
  and the candidate was recreated with the original networks and configuration.
  Local `pg_isready` and n8n health returned successfully with no new fatal or
  DNS errors after convergence.
  Ollama `0.40.13` was then applied to VM100 CouchLoom after a validated
  `ollama_data` archive; the embedding model remained present and both Ollama
  and CouchLoom stayed healthy. The inventory audit also corrected Cloudflared:
  it is a flapping native Pi5 systemd unit, not a live Docker service. The
  native ARM64 binary was upgraded from `2026.2.0` to `2026.10.7` with a
  rollback copy, but a direct launch still returns `Unauthorized: Tunnel not
  found`; the existing token/tunnel must be repaired before accepting the
  public route. The older VM100 BDS connector entry is retired/absent. GitLab
  was intentionally skipped after its native backup grew too large for this
  window, so its staged `18.11.14` → `19.2.10` → `19.5.3` path remains future
  work. Databasus later passed its volume/key, provider-backup and restore
  gates for the six approved service databases; non-service jobs remain a
  separate scope decision.
  cAdvisor `v0.55.1` was also upgraded on Pi5 with a Compose/spec backup; its
  container stayed healthy and exposed the expected versioned metrics.
  RustFS `1.0.4` was then upgraded from `1.0.1` after a validated 1.22 GB
  data archive; its ARM64 binary, internal API/console health, and public S3/
  console health routes returned successfully, with the old image retained for
  rollback.
  CouchDB `3.5.3` followed with a validated 702 MB data archive; the
  authenticated root/database and `_changes` checks passed, the Obsidian
  document count stayed at `49341`, and both public routes retained their
  expected unauthenticated `401` boundary.
  PostgreSQL/pgvector then moved from PostgreSQL `16.14` to `16.15` on a
  pinned digest after a checksummed `59M` logical backup of all `17` databases;
  a candidate scratch restore of `n8n` passed, the vector extension remained
  present, PgBouncer accepted connections, and n8n health stayed `200`.
  Pi5 Redis moved from `7.2.15` to `7.2.17` on a pinned digest after an RDB
  snapshot, AOF/data archive and scratch RDB restore (`DBSIZE=10`); AOF and
  `PING` remained healthy. RelayHub's active Swarm Redis was already on the
  current `7.4.12` digest, and its legacy non-persistent Compose Redis was
  recreated with the same pin; API/worker health and public HTTP 200 held.
  GitLab CE was intentionally skipped after its native backup grew to a
  multi-GB operation; no GitLab image changed. Databasus `v3.64.0` was first
  rolled back after the existing `THREE_MONTH` retention value caused the
  backup cleaner goroutine to panic on startup. A fresh 29.3 MB volume archive
  was then taken, all 15 invalid logical retention values were changed in a
  transaction to the source-supported `3_MONTH`, and the verified amd64
  candidate digest was applied. Version `3.64.0`, internal health, public root,
  migrations and the cleaner startup now pass without a fresh panic. A Pi5
  `pi-verifier-1` restore-verification agent was registered and started under
  `databasus-verification-agent.service` with a one-job limit; the first manual
  n8n restore check passed (`pg_restore` exit `0`, `153` tables, `52.58 MB`,
  `2s`). `After backup` verification is enabled for n8n, homelab, relayhub and
  the three NetBird PostgreSQL databases. Provider-authenticated backup
  evidence and remaining approved-service restore checks remain open. A new
  n8n backup after the Databasus upgrade then completed successfully and its
  automatic restore check passed with `pg_restore` exit `0`, `190` tables and
  `54.76 MB` restored. The same provider + restore gate then passed for
  homelab, relayhub, netbird, netbird_activity and netbird_idp; all six
  approved service databases now show `Verified`.
  The Pi5 Traefik tag `v3.6` was checked against `v3.6.25`; its OCI image label
  already reports `v3.6.25`, so no edge restart was needed. AdGuard Home
  `v0.107.79` was also pulled and reported up to date.
  A two-agent read-only backlog audit then reconciled current evidence: U2/U3/U4/U6
  and B13 were marked done; U1/U5/U7/U9 remain partial; B2/B4/B5/B8 were
  reopened because the corresponding VM100 timers are disabled/inactive. GitLab
  remains skipped and Cloudflared remains explicitly deferred by the operator.

- **VPS gateway live audit 2026-10-31:** repaired the read-only audit path by
  deriving the existing Gateway SSH key from 1Password into a mode-`0600`
  temporary file; the server-accepted fingerprint matched and the temporary
  file was removed after use. The host reported 4 vCPU, 7.8 GiB RAM with
  7.0 GiB available, 38 GiB root with 20% used, Docker `29.3.0`, no failed
  systemd unit, and nine running gateway containers with restart count `0`.
  Local SNI smoke returned relay `404`, GitLab `302`, and homepage `200`; all
  intended TCP listeners and host UDP bindings were present. No VPS mutation
  was performed. None of the containers has a Docker healthcheck, UFW is
  inactive, and authenticated NetBird/RustDesk session tests remain open. Full
  evidence: [VPS gateway live audit](./deployments/vps-gateway-audit-2026-10-31.md).

- **Documentation visual flow 2026-10-31:** added five validated SVG diagrams
  for system topology, VPS gateway, data/backup ownership, NetBird relay
  boundaries and upgrade/restore flow. Added a sixth project/reference-note
  flow showing the source checkout → inventory → release evidence → status and
  backlog path, plus the authority order from current status through dated
  evidence and runbooks to historical notes. The diagrams are linked from
  `INDEX.md`, `PROJECTS.md`, `STACK.md`, `PI.md`, the backup runbook, the VPS
  audit and the version-upgrade ledger; no runtime or infrastructure changed.

- **Project cleanup 2026-10-31:** moved the standalone
  `/home/dungxbuif/workspace/projects/obsidian-livesync` checkout (22 MiB,
  clean Git worktree) to the desktop Trash. The checkout was not listed in
  `PROJECTS.md`; no CouchDB data, LiveSync runtime, Homelab note or other
  project was deleted. The Trash move remains recoverable.

- **Project cleanup 2 2026-10-31:** moved the clean local checkouts
  `mezon` (238 MiB), `urbanx-sample` (7.3 MiB), and `harness-experimental`
  (4.7 MiB) to the desktop Trash. `repository-harness` was not a separate
  local folder; it was the redirected upstream name for `harness-experimental`.
  No runtime service, Mezon webhook, or infrastructure state was changed.

- **Project inventory reconciliation 2026-10-31:** reconciled `PROJECTS.md`
  against `/home/dungxbuif/workspace/projects/`: added `MyPocket`, `RelayHub`,
  `k8s-syntax`, `llm-flashcard`, `apps` and `n8n-nodes-mezon`; removed stale
  rows for `goclaw`, `harness-experimental`, `mezon`, `open-design` and
  `urbanx-sample`; and excluded the dangling `mezon-go-sdk` compatibility
  symlink. The current table now represents 46 real directories.

- **GitLab mirror preflight 2026-10-31:** the local GitLab API token reference
  was found in the ignored `db-management/local_vars.json` file with mode
  `0600`; its value was never printed or written to a remote URL. Authenticated
  requests to `/api/v4/version`, `/api/v4/user` and `/api/v4/projects` all
  returned `HTTP 500`, so no GitLab projects were created, no source was
  pushed, and no local remotes were changed. R7 is blocked on repairing the
  GitLab API/route, after which the approved 46-project scope can be resumed.

- **GitLab route isolation 2026-10-31:** a read-only VM100 probe found the
  GitLab `18.11.11` task healthy, `/-/health` and `/-/readiness` returning
  `200`, and the internal unauthenticated API returning the expected `401`.
  The public `gitlab.dungxbuif.com/api/v4/*` requests still return `500`, so
  R7 is blocked at the public API/tunnel boundary rather than by a stopped
  GitLab container. No runtime or source state was changed.
