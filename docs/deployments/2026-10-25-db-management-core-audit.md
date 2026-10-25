# DB-management core audit — 2026-10-25 (updated)

## Production-readiness recheck — 2026-10-26 00:46 ICT

This section supersedes the older rehearsal notes below where they describe
the release boundary as pending. It records the latest observed state; it does
not close the restore, Databasus, or legacy-retirement gates.

- GitLab tag pipeline [#516](https://gitlab.dungxbuif.com/dungxbuif/db-management/-/pipelines/516)
  passed quality, ops-contract, image build, container scan, and
  release-manifest. The manifest recorded app commit
  `5f300d5619c8c782d404ecc259dd860e9cc01ba9`, ops commit
  `7f2b868136b7e55fe706bf1a8342d6dbc98d4eb6`, and the three immutable API,
  worker, and web image digests.
- Manual deploy job `1590` completed successfully. Its receipt verified the
  manifest, service allowlist, Swarm convergence, and HTTPS readiness; the
  observed service image references matched the requested digests. The
  protected `DB_MANAGEMENT_DEPLOY_APPROVED` variable was reset to `false`
  immediately after the deployment.
- The dedicated Pi5 release identity is enrolled with a forced command,
  root-owned helper, host lock, private receipts, and strict known-hosts
  verification. The enrolled ops SHA is the same immutable SHA recorded by
  pipeline `516`; the identity has no shell, forwarding, TTY, or Docker-group
  access.
- Pi5 LAN DNS was corrected to use AdGuard at `10.10.0.5` through Netplan.
  From Pi5, `db-management.dungxbuif.com` now resolves to `10.10.0.5` and
  `/health/ready` returns API and worker `ok`; the previous public-VPS
  certificate mismatch is no longer observed on that host.
- After deployment, all five stack services were `1/1`: API, worker, web,
  CloudBeaver, and Databasus. Strict HTTPS checks from the workstation
  returned HTTP `200` for all three private routes and resolved them to
  `10.10.0.5`.
- A fresh four-source backup rehearsal was started through the API. PostgreSQL
  (`0615effb-947c-4a33-bc49-fc6ef385fdae`), CouchDB Obsidian
  (`f2fe3ca8-afdb-4ca9-81a2-b875c2bc7f12`), and Couchloom PostgreSQL
  (`7b96b3d1-8042-492c-9279-845233a0a8e9`) reached `succeeded`. CouchDB
  Homelab (`c5fce5b0-50fe-43af-83da-7eee0949985a`) was still `running` with
  active worker heartbeat at this audit timestamp; its final result is not
  claimed here. The large staging payload was approximately 6.08 GB and the
  worker remained running without OOM/restart.

## Current deployment

- Swarm stack `db-management` runs on VM110 (`10.10.0.32`); Pi5 remains the
  data and LAN edge host.
- The live application release observed on the Swarm manager is
  `6a382fe-drivefix2-20261025T1135Z`. API, worker, web, CloudBeaver, and Databasus
  were all `1/1` at the read-only check.
- The worker uses direct, resumable Google Drive SDK uploads. It does not run
  Restic or rclone.
- The worker-only external secret name is
  `db-management-drive-credentials-v2`. No credential value is recorded here.
- The active destination is documented by label only as
  `Homelab Backup/databases`; the Drive folder ID is intentionally omitted.
- The deployed retention policy is seven days for successful Drive run
  folders. Completed local staging is configured with `keep=0` after verified
  upload; failed, incomplete, and stale evidence is preserved.

## Drive incident and correction

The missing visible records were caused by the previous Drive destination
resolving to the `homelab-backups` database folder, which had been moved to
Trash. Upload attempts therefore did not land in the active operator-visible
database backup path. The v2 worker secret now points at the active
`Homelab Backup/databases` destination, and the runtime path is the native
Drive SDK rather than the old Restic/rclone transport. A fresh PostgreSQL
verification job (`12867fd9-7b71-4599-93f9-accc5ce32d23`) was observed
`succeeded`; direct Drive API inspection found its source/run folder and
top-level control files under the active destination.

This note records the root cause and the path label only. It does not record a
folder ID, OAuth value, token, or secret contents.

## Verification evidence

The following evidence was observed without printing secret material:

| Check | Result |
| --- | --- |
| API/worker health | API liveness and worker heartbeat were healthy on the VM110 deployment |
| Swarm convergence | API, worker, web, CloudBeaver, and Databasus were each `1/1` |
| Native backup jobs | `12867fd9` (PostgreSQL), `b532c3b3` (CouchDB Obsidian), `c6ad4d05` (Couchloom PostgreSQL), and `e39e79f6` (CouchDB homelab) all reached `succeeded`; each active Drive run has `COMPLETE`, `manifest.json`, `checksums.sha256`, and its payload directory |
| Large CouchDB run | A manual full-image run completed with Drive receipt and no worker OOM/restart |
| Local retention contract | Runtime configuration is seven-day remote retention and completed staging `keep=0`; the four verified staging directories were absent after upload |
| LAN route check | Direct DNS query to Pi5 DNS (`10.10.0.5`) and this workstation's current resolver return the LAN address; strict HTTPS requests without `--resolve` return `200` for all three local routes. The Pi5 host resolver itself remains a separate exception described below |

These checks prove deployment health and upload/receipt integrity. They do not
prove a full isolated restore for every source.

## Follow-up live recheck — 2026-10-25 23:40 ICT

The read-only API and Swarm checks were repeated after the initial evidence was
written:

- `db-management_db-management-{api,worker,web}`, CloudBeaver and Databasus
  were all `1/1`.
- `health/ready`, CloudBeaver `/status`, and Databasus
  `/api/v1/system/health` each returned HTTP `200` through Pi5 LAN routing.
- The worker reported `DB_MANAGEMENT_BACKUP_STORAGE_REQUIRED=true`, seven-day
  Drive retention, and completed staging `keep=0`; the Drive, backup and Mezon
  credentials were mounted as worker-only Swarm secrets.
- The latest successful native jobs remained PostgreSQL
  `12867fd9-7b71-4599-93f9-accc5ce32d23`, CouchDB Obsidian
  `b532c3b3-a6f7-447e-bedf-84750a3dea17`, Couchloom PostgreSQL
  `c6ad4d05-bb0f-41ae-b8ef-1dd16d206ef8`, and CouchDB Homelab
  `e39e79f6-9275-4116-83a4-ff1aa9363637`.
- The API currently exposes five catalog sources. CouchDB Homelab, CouchDB
  Obsidian and Redis returned live `status: ok`; Redis metrics reported Redis
  `7.2.15`, no rejected connections and no evicted keys at the check. The two
  PostgreSQL sources returned the intentional CloudBeaver bookmark result
  (`unsupported`) rather than an unverified direct database claim.
- The job history still contains earlier failures: Couchloom authentication
  against the old `15432` relay and one large CouchDB run that hit worker
  `ENOMEM`. They remain visible as historical evidence; later runs succeeded
  after the relay correction and large-run follow-up.
- AdGuard itself answers all three local names with `10.10.0.5`, and the
  workstation now passes strict HTTPS without `--resolve`. The Pi5 host's
  static `/etc/resolv.conf` still points at `1.1.1.1`; a strict curl from Pi5
  therefore resolves the public VPS certificate and fails hostname
  verification. This is a host/DHCP resolver issue, not an application TLS
  issue; Pi5-local normal-DNS acceptance remains open until its resolver source
  is fixed and verified without `--resolve`.

This recheck strengthens current availability and monitoring evidence only. It
does not close protected release/rollback, isolated restore, or Databasus
provider acceptance gates.

## Boundaries and remaining gates

### CI provenance rehearsal

- GitLab pipeline [#489](https://gitlab.dungxbuif.com/dungxbuif/db-management/-/pipelines/489)
  passed quality, the reviewed ops branch contract (`43` tests plus `29` route
  checks), image build, digest-pinned Trivy scan and release-manifest creation.
- Its manifest recorded app commit `0bc381d352bf4cb07fbbfc993658241d67c819f2`,
  ops commit `0c10c331f7d5a9bfc5bf0205928e32b1309a937a`, pipeline `489`, and
  exactly three registry `sha256` image digests. No secret or command output was
  included in the artifact.
- The deploy job remained manual and was not started. GitLab project variables
  currently contain the older VM110 key and inventory, but the dedicated
  `DB_MANAGEMENT_RELEASE_PRIVATE_KEY` and pinned
  `DB_MANAGEMENT_SSH_KNOWN_HOSTS` file required by the new no-1Password deploy
  path are not yet present. The app commit `1b7c02e` now calls the restricted
  Pi5 release client instead of the Ansible normal-release path; ops commit
  `42b52d3` adds the root-owned forced-command helper, host lock, private
  receipts, stale-pipeline check, bounded manual rollback, and HTTPS API/worker
  readiness probe. These changes are pushed but not enrolled or run against
  production.
- Branch rehearsal [#493](https://gitlab.dungxbuif.com/dungxbuif/db-management/-/pipelines/493)
  passed quality and ops contracts. Tag rehearsals [#496](https://gitlab.dungxbuif.com/dungxbuif/db-management/-/pipelines/496)
  and [#501](https://gitlab.dungxbuif.com/dungxbuif/db-management/-/pipelines/501)
  were created with `OPS_REF=codex/task1-migration-inventory` to exercise the
  build/scan/manifest path; #496 was canceled, while #501 passed quality,
  ops-contract (including the release/verifier suite), image build, digest scan,
  and manifest creation. Its manifest records app `9d62b05c8b36a79c52d448c942eb1ced70f1a544`,
  ops `42b52d3eb0a8b5061d292c43f8b853a37931a449`, pipeline `501`, and three
  registry digests. #501 stopped at `deploy-vm110: manual`; no deploy job has
  been started.
- Branch pipeline [#506](https://gitlab.dungxbuif.com/dungxbuif/db-management/-/pipelines/506)
  passed `quality` and `ops-contract` against app commit `2890a13` and ops
  ref `codex/task1-migration-inventory`, including the private-DNS verifier
  contract. It was intentionally unprotected, so it did not build release
  images or create a deploy job.
- App merge-request pipeline [#507](https://gitlab.dungxbuif.com/dungxbuif/db-management/-/pipelines/507)
  passed `quality` but its `ops-contract` failed because the automatic MR
  context resolved the project default `OPS_REF=main`, which predates the
  release-contract files on the ops feature branch. This is a cross-repository
  MR wiring issue, not evidence that the feature ops contract passed in that
  pipeline; the passing #506 branch pipeline used the explicit ops ref. The
  subsequent automatic branch/MR pipelines #508 and #509 reproduced the same
  default-ops-ref failure.
- Commit `d2df9b7b161bf5583b53c5a1f9f3967edf96dc11` fixes that wiring at the
  source: `.gitlab-ci.yml`, the release-manifest contract test, and the CI
  runbook now require a full immutable ops SHA. The GitLab project variable
  `OPS_REF` was updated to the same reviewed ops commit
  `8df7d0c5626973eb810a42526ab89d0bbcc454bb`, so it cannot override the pin
  with `main`. Push pipeline [#510](https://gitlab.dungxbuif.com/dungxbuif/db-management/-/pipelines/510)
  and MR pipeline [#511](https://gitlab.dungxbuif.com/dungxbuif/db-management/-/pipelines/511)
  both passed `quality` and `ops-contract`; the ops job fetched that exact SHA,
  ran 59 tests, and completed `verify-routes.sh`.

- CloudBeaver is the PostgreSQL administration tool boundary/bookmark. Its
  container being healthy is not proof of a verified PostgreSQL session,
  permission model, backup, or restore through db-management.
- Databasus is a separate UI/provider boundary. Its service is healthy, but a
  Databasus workspace, provider/storage configuration, backup, remote snapshot,
  and isolated restore are not recorded as verified. db-management therefore
  keeps Databasus inventory `unsupported` rather than claiming an empty
  successful provider inventory.
- Direct Drive upload and metadata checks are not an immutable backup or a
  restore test. Run and record isolated restores for the required production
  sources before calling the migration fully accepted.
- Restic/rclone, the old backup scripts, and Semaphore were not globally
  deleted in this update. They are outside the active db-management runtime,
  but may still exist or run as separate legacy lab components until a
  consumer inventory and approved retirement are completed.
- The service remains LAN/NetBird scoped and has no application authentication
  flow; broader exposure is not part of this deployment evidence.
- On clients with a higher-priority NetBird `~.` DNS route, use the lab DNS
  path or fix DNS route priority before treating the public/default-Traefik
  response as an application failure. This is a client DNS/routing gate, not
  a db-management container failure.

## Next acceptance gates

1. Enroll the dedicated Pi5 release identity with the exact reviewed ops SHA,
   add the two protected file variables, then run the manual M1 deploy and
   verify its receipt and observed digests.
2. Complete isolated restore acceptance for each required native source and
   retain only secret-free evidence.
3. If Databasus is retained, configure and verify its private workspace,
   provider/storage, backup, and isolated restore separately.
4. Inventory consumers of the old scripts and Semaphore, then approve their
   retirement independently; do not infer global deletion from the new worker
   image.
