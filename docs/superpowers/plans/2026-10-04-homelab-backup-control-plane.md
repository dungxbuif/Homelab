# Homelab Backup Control Plane Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a private UI and automation workflow for database provisioning plus online PostgreSQL/CouchDB, RustFS, and GitLab backups to encrypted Google Drive repositories with verified retention and restore tests.

**Architecture:** Semaphore is the private operator UI and job history surface. Ansible provides idempotent provisioning and backup orchestration, while engine-specific scripts perform native exports. VM100 is the target automation/backup runner; Pi5 remains the datastore and RustFS host. The first Semaphore UI pilot runs portlessly on Pi5 over the existing private proxy network so the operator workflow can be verified immediately. Restic encrypts and versions backup runs, and rclone only transports the three dedicated repositories to Google Drive.

**Tech Stack:** Semaphore UI, Ansible, PostgreSQL native tools, CouchDB HTTP/replication tooling, GitLab Omnibus `gitlab-backup`, RustFS S3-compatible API/`rc`, restic, rclone, Docker Swarm secrets, Google Drive OAuth.

**Spec:** `docs/superpowers/specs/2026-10-04-homelab-backup-control-plane.md`

## Global Constraints

- Keep Pi5 as the datastore host and VM100 as the target automation/backup host. The
  current Semaphore pilot may run on Pi5, but it is private-only and not the final
  runner placement.
- Do not back up Redis or NATS.
- Do not stop PostgreSQL, CouchDB, RustFS, GitLab, or other production services during scheduled backups.
- Do not use live-volume `rsync` as the scheduled RustFS or GitLab mechanism.
- Use GitLab native backup for GitLab application data; preserve required GitLab configuration/secrets separately within the GitLab backup workflow.
- Use three encrypted restic repositories transported by rclone to dedicated Google Drive locations.
- Retain 14 daily, 8 weekly, and 12 monthly snapshots; prune only after successful upload and repository verification.
- Keep the control UI private over LAN/NetBird with no public route or new database host port.
- Never commit, print, or expose credential values.
- Preserve unrelated dirty worktree changes and do not perform destructive production cleanup without explicit approval.

## Review Focus

- A failed export must never be marked as a complete backup: test failure aggregation in the backup runner task.
- A missing or expired Drive token must stop before prune: test preflight and no-delete behavior in the retention task.
- A live GitLab backup must not assume Redis is recoverable: test the coverage manifest and restore notes in the GitLab task.
- A live RustFS export must preserve object identity sufficiently for restore: test manifest/checksum verification in the RustFS task.
- A provisioning request must not execute arbitrary SQL or expose generated passwords: test validation, least-privilege execution, and secret references in the provisioning task.

---

### Task 1: Freeze Inventory and Backup Policy

**Files:**
- Create: `backup/policies.yaml`
- Create: `backup/inventory.yaml`
- Create: `backup/README.md`
- Modify: `docs/STACK.md`
- Modify: `docs/PI.md`
- Modify: `docs/services/gitlab.md`

**Interfaces:**
- Produces the canonical engine/app/bucket catalog consumed by all later Ansible jobs.
- Produces policy IDs `db-default`, `rustfs-default`, and `gitlab-default` with the fixed 14/8/12 retention values.

- [ ] Record the verified PostgreSQL database list, CouchDB database list, GitLab service/container identity, GitLab version, RustFS bucket list, and current RustFS volume topology without reading secret values.
- [ ] Mark Redis, NATS, arbitrary application files, and unapproved object buckets as excluded.
- [ ] Record the Drive destination prefixes and whether the account is personal Drive or Shared Drive.
- [ ] Define staging path `/var/lib/homelab-backup/runs` on VM100 and minimum free-space checks.
- [ ] Document that GitLab `gitlab-backup create` may require `rsync` internally, while no custom live-volume rsync job is installed.
- [ ] Verify the inventory parser rejects unknown engines and duplicate database/bucket identifiers.
- [ ] Run: `python3 backup/scripts/validate_inventory.py backup/inventory.yaml backup/policies.yaml`.
- [ ] Expected: exit `0` with no secret values printed.

### Task 2: Deploy Private Semaphore and Secret Boundary

**Files:**
- Create: `automation/semaphore/stack.yml`
- Create: `automation/semaphore/README.md`
- Modify: `docs/INDEX.md`

**Interfaces:**
- Produces private Semaphore UI reachable only through LAN/NetBird.
- The final deployment will produce job templates named `db-provision`,
  `db-backup`, `gitlab-backup`, `rustfs-backup`, `backup-retention`, and
  `restore-test`; the current pilot intentionally does not enable them.

- [ ] Choose a dedicated PostgreSQL database for Semaphore/control metadata and add it to `backup/inventory.yaml`; do not use Redis.
- [x] For the immediate pilot, deploy Semaphore on Pi5 with SQLite, no host port,
  and only the existing `homelab-net` overlay. Do not add a production database
  or enable backup jobs in the pilot.
- [ ] Move the validated UI and runner to VM100 with a dedicated PostgreSQL
  database before enabling production schedules.
- [ ] Store Semaphore DB credentials, Drive OAuth/rclone configuration, restic passwords, and engine credentials as private secrets.
- [ ] Configure a single scheduler owner in Semaphore; do not create duplicate cron/systemd schedules.
- [x] Verify the UI is unreachable from the public ingress and reachable from the approved private path.
- [ ] Verify a no-op Semaphore template can run and records status without mutating a datastore.

### Task 3: Implement Declarative Database Provisioning

**Files:**
- Create: `iac/ansible/roles/db_provision/tasks/main.yml`
- Create: `iac/ansible/roles/db_provision/templates/catalog-entry.yml.j2`
- Create: `iac/ansible/db-provision.yml`
- Create: `backup/scripts/validate_provision_request.py`
- Create: `backup/provision-request.example.yaml`
- Modify: `backup/inventory.yaml`
- Modify: `docs/PI.md`

**Interfaces:**
- Input: `backup/provision-request.yaml` with `engine`, `name`, `application`, `environment`, owner identity, and policy ID.
- Produces: an idempotent database/role/security policy and a catalog entry containing only secret references.

- [ ] Write validation tests for safe names, supported engines, duplicate names, forbidden system names, and missing policy IDs.
- [ ] Implement PostgreSQL creation with Ansible PostgreSQL modules, least-privilege grants, approved extensions only, and generated secret references.
- [ ] Implement CouchDB database/user/security creation through its authenticated HTTP API, with no arbitrary request body from the UI.
- [ ] Make rerunning the same request produce no destructive changes and no password output.
- [ ] Run provisioning first against disposable `staging` names, then verify PostgreSQL `SELECT 1` and CouchDB authenticated read.
- [ ] Promote the Semaphore template only after the idempotency and permission tests pass.

### Task 4: Build PostgreSQL and CouchDB Online Backup Runner

**Files:**
- Create: `backup/scripts/backup-postgres.py`
- Create: `backup/scripts/backup-couchdb.py`
- Create: `backup/scripts/run-database-backup.py`
- Create: `backup/tests/test_database_backup.py`
- Create: `automation/backup-runner/compose.yml`
- Modify: `backup/inventory.yaml`

**Interfaces:**
- `run-database-backup.py --inventory backup/inventory.yaml --policy db-default --run-id <id>` returns non-zero for any required target failure.
- Produces `manifest.json`, checksums, PostgreSQL custom-format dumps/globals, and CouchDB logical exports in an incomplete run directory before atomically marking completion.
- Does not connect to Redis or NATS.

- [ ] Add failing tests for one failed database, a missing credential reference, insufficient staging space, and a successful multi-engine run.
- [ ] Export PostgreSQL databases directly from the private PostgreSQL service, not through PgBouncer, using `pg_dump` and a separate globals export.
- [ ] Implement CouchDB online logical export/replication with system database and security metadata coverage recorded in the manifest.
- [ ] Add checksums, engine versions, database names, export times, and source endpoint identifiers without passwords.
- [ ] Add the global lock and incomplete/complete state transitions.
- [ ] Run against one disposable PostgreSQL database and one disposable CouchDB database while production services remain up.
- [ ] Verify a selected dump can be restored into isolated targets before enabling the full inventory.

### Task 5: Add GitLab Native Online Backup Workflow

**Files:**
- Create: `automation/gitlab-backup/run-gitlab-backup.sh`
- Create: `automation/gitlab-backup/README.md`
- Create: `automation/gitlab-backup/coverage-manifest.py`
- Create: `backup/tests/test_gitlab_backup_contract.py`
- Modify: `docs/services/gitlab.md`
- Modify: `backup/inventory.yaml`

**Interfaces:**
- `run-gitlab-backup.sh` runs inside the current `gitlab_gitlab` Omnibus container using `gitlab-backup create` and the supported configuration backup command without stopping the service.
- Produces a GitLab backup archive, configuration/secrets artifact, version/edition manifest, and Redis-excluded coverage note.

- [ ] Test that the wrapper refuses to run if no healthy `gitlab_gitlab` task is found or if the discovered GitLab version is not recorded.
- [ ] Run the native GitLab backup online and retain the generated archive in the staging directory.
- [ ] Run the supported configuration/secrets backup for `gitlab.rb` and `gitlab-secrets.json`; never print their contents.
- [ ] Record that current local filesystem registry data is covered, while future object-storage-backed data requires a separate RustFS/object-storage policy.
- [ ] Record that Redis DB 2, sessions, cache, and Sidekiq queues are not backed up.
- [ ] Verify an archive exists, is non-empty, matches the current GitLab version, and can be inspected without production restore.
- [ ] Perform one isolated restore rehearsal on the same GitLab version before enabling daily scheduling.

### Task 6: Add RustFS Online Object Backup

**Files:**
- Create: `automation/rustfs-backup/export-buckets.py`
- Create: `automation/rustfs-backup/README.md`
- Create: `backup/tests/test_rustfs_manifest.py`
- Modify: `backup/inventory.yaml`
- Modify: `docs/PI.md`

**Interfaces:**
- `export-buckets.py --endpoint <private-s3-endpoint> --inventory backup/inventory.yaml --run-id <id>` exports approved buckets through the S3-compatible API while RustFS remains available.
- Produces one manifest per bucket and a restic-ready export directory tagged by bucket.

- [ ] Add failing tests for an unapproved bucket, checksum mismatch, incomplete multipart object, and missing version metadata.
- [ ] Enable or verify bucket versioning only after recording current bucket state and receiving approval for any bucket-level setting change.
- [ ] Export current object content, metadata, checksums/ETags, and available version IDs through `rc` or an S3-compatible client.
- [ ] Make source deletes non-destructive to the staging directory; never use `rclone sync --delete` from RustFS to staging.
- [ ] Document stopped-volume `rsync` as emergency cold recovery only, including the requirement to stop RustFS and preserve ownership/metadata.
- [ ] Restore a selected bucket/object set into an isolated RustFS target and compare manifest/checksum results.

### Task 7: Add Restic/rclone Google Drive Transport and Retention

**Files:**
- Create: `backup/scripts/upload-restic.sh`
- Create: `backup/scripts/verify-retention.sh`
- Create: `backup/scripts/restore-staging.sh`
- Create: `backup/tests/test_retention_policy.py`
- Create: `automation/backup-runner/retention.env.example`
- Modify: `backup/policies.yaml`
- Modify: `docs/research/google-drive-db-backup-2026-09-13.md`

**Interfaces:**
- `upload-restic.sh --class databases|rustfs|gitlab --run-dir <completed-run>` creates/verifies one tagged snapshot in the matching encrypted repository.
- `verify-retention.sh --class <class>` performs `restic check`, then applies 14 daily/8 weekly/12 monthly retention only to that repository.

- [ ] Add failing tests for prune after failed upload, wrong repository prefix, missing restic password, and a policy that would delete a required recovery point.
- [ ] Create separate Drive repositories/prefixes `homelab-backups/databases`, `homelab-backups/rustfs`, and `homelab-backups/gitlab`.
- [ ] Configure rclone with a dedicated Google Drive remote and a separate RustFS source remote; never mount Google Drive as a filesystem.
- [ ] Upload only complete manifests/runs and record restic snapshot IDs in Semaphore output.
- [ ] Run repository check before prune and skip all deletion if check or upload fails.
- [ ] Configure permanent deletion only for the dedicated backup remote after testing a disposable Drive folder; never delete outside the three prefixes.
- [ ] Verify quota, snapshot listing, retention selection, and recovery download before enabling the 05:30 maintenance schedule.

### Task 8: Schedule, Alerts, and Restore Tests

**Files:**
- Create: `automation/semaphore/templates/schedule.yaml`
- Create: `backup/scripts/health-report.py`
- Create: `backup/tests/test_schedule_contract.py`
- Create: `docs/runbooks/backup-restore.md`
- Modify: `backup/scripts/post-check-report.sh`
- Modify: `backup/scripts/notify-mezon.sh`
- Modify: `docs/STACK.md`
- Modify: `docs/INDEX.md`
- Modify: `docs/LOG.md`

**Interfaces:**
- Schedule is `Asia/Ho_Chi_Minh`: database 01:00, GitLab 02:30, RustFS 04:30, retention 05:30.
- `health-report.py` reports last successful snapshot, covered targets, repository check, quota, staging free space, and last restore-test timestamp without secret values.

- [ ] Configure one global lock so the four jobs cannot overlap.
- [ ] Add alerts for any required export failure, Drive authentication failure, quota threshold, staging disk threshold, or last successful snapshot older than 26 hours.
- [ ] Send one sanitized Mezon webhook status only after each class post-check passes; send a failure status and non-zero exit for a failed check.
- [ ] Keep the webhook URL in a runtime secret file or secret mount and test that dry-run output never includes the URL.
- [ ] Add monthly isolated restore tests for one PostgreSQL database, one CouchDB database, one RustFS bucket/object set, and one GitLab disposable target.
- [ ] Verify no scheduled task stops or scales down production services.
- [ ] Run two consecutive dry-run windows, then one real pilot window, before enabling the full schedule.
- [ ] Reconcile `STACK.md`, `PI.md`, `VM100.md`, GitLab runbook, backup research, and changelog with the deployed state.

### Task 9: Final Verification and Handoff

**Files:**
- Modify: `docs/runbooks/backup-restore.md`
- Modify: `docs/services/gitlab.md`
- Modify: `docs/PI.md`
- Modify: `docs/VM100.md`
- Modify: `docs/STACK.md`

- [ ] Run inventory validation, Ansible syntax checks, shell syntax checks, unit tests, and a Semaphore no-op job.
- [ ] Run a complete backup window and record all three repository snapshot IDs.
- [ ] Confirm Redis and NATS produced no backup artifacts.
- [ ] Confirm public ingress has no route to Semaphore or the backup runner.
- [ ] Run the restore rehearsal and record evidence, limitations, and exact version requirements.
- [ ] Verify retention removes only expired objects from the three dedicated repositories and leaves unrelated Google Drive data untouched.
- [ ] Commit only the implementation and documentation files belonging to this plan; leave unrelated worktree changes untouched.
