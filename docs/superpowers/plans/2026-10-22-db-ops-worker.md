# DB Operations Worker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create a dedicated VM for backup and database-operations workloads while keeping production databases on Pi5 and user-facing applications on VM100.

**Architecture:** Clone the existing Ubuntu cloud-init template as VM110 on the same Proxmox node, allocate 4 vCPU, 8 GiB RAM and 80 GiB local-lvm disk, and assign `10.10.0.32`. Install the existing backup runtime and DB-operations tooling on VM110 through Ansible. Migrate one scheduler class at a time with success markers, leaving a rollback path on VM100 until acceptance passes.

**Tech Stack:** Proxmox API, Ubuntu 22.04 LTS cloud-init, Docker/Ansible, systemd timers, existing native PostgreSQL/CouchDB/RustFS/GitLab backup clients.

**Spec:** `docs/STATUS.md`, `docs/STACK.md`, `docs/runbooks/backup-restore.md`, `docs/BACKLOG.md`.

## Global Constraints

- Pi5 remains the production data host; do not move PostgreSQL, CouchDB, Redis or RustFS data stores.
- VM100 remains the production application host; do not remove its backup runtime until VM110 acceptance passes.
- VM110 has no public ports and is reachable only over the LAN/private management path.
- VM110 may run Docker as a client runtime for pinned one-shot backup tools; it
  must not publish application or database ports.
- VM110 bootstrap repairs an interrupted package transaction inherited from the
  Ubuntu template before installing prerequisites.
- The existing systemd backup scheduler remains the single scheduler; Semaphore does not duplicate it.
- Credentials are injected through the existing secret mechanism and are not committed to Git.
- VM110 is on the same Proxmox/local-lvm failure domain; it improves workload isolation but is not a second backup failure domain.

## Review Focus

- A failed VM110 job must leave the previous VM100 marker intact and alert as failed.
- A partial migration must not create overlapping backup jobs or concurrent retention locks.
- VM110 must reach Pi5 services privately without exposing database ports publicly.
- GitLab native backup must run beside the GitLab filesystem on VM100 until a supported pull/restore path is proven.
- Disk pressure on VM110 must stop a job before it creates incomplete remote state.

### Task 1: Create and verify VM110

- Clone template `9000` to VMID `110` on `local-lvm`.
- Configure `db-ops`, 4 vCPU, 8192 MiB RAM, 80 GiB disk, cloud-init user and `10.10.0.32/24`.
- Verify guest agent, SSH, DNS, disk, swap and no published services.
- Current evidence: SSH, DNS, disk and private reachability pass. Guest agent
  enrollment is blocked by the cloned template's interrupted `dpkg` state and
  loss of passwordless sudo after package repair; no scheduler was enabled.
- VM110 was rebuilt from the template, its disk was expanded to 80 GiB, and the
  guest root filesystem was grown online.

### Task 2: Install the operations runtime

- Package the existing backup scripts and required native clients through Ansible.
- Add DB-operations wrappers for read-only inventory, migration rehearsal, restore staging and provisioning.
- Keep secrets short-lived and scoped per operation.
- Run the existing contract and post-check tests.
- Do not migrate runtime or credentials until the VM image/bootstrap privilege
  path is repaired and a fresh Ansible apply succeeds end to end.
- The staged runtime must include both Restic container helpers
  (`prepare_rclone_workdir.py` and `run_restic_container.py`); a missing helper
  is a deployment failure even when shell/Python syntax checks pass.
- Runtime deployment removes stale root-owned Python `__pycache__` directories
  before non-root syntax validation so an earlier privileged check cannot block
  a later release.
- VM110 uses the pinned minimal Restic image with Ubuntu's packaged dynamic
  `rclone`; the runner mounts only its required loader and libc paths rather
  than switching to an unpinned image or host-side Restic.
- The shared runner uses rclone's valid `64M` chunk-size spelling; `64Mi` is
  rejected by rclone and is not a valid substitute here.

### Task 3: Migrate backup classes safely

- Migrate `database-instances`, `databases`, RustFS and restore-drill one class at a time.
- Pause the corresponding VM100 timer only after VM110 is installed and preflight passes.
- Require one successful remote post-check and one restore/manifest check before disabling VM100 rollback.
- Keep GitLab backup on VM100 until a native filesystem-consistent alternative is accepted.
- The CouchDB proxy cutover gate requires the live Pi5 allowlist to include
  VM110 (`10.10.0.32/32`) alongside VM100; until that exact live change is
  applied and a `200` probe passes, the `databases` timer remains on VM100.
- VM110 reaches the existing private data paths through a VM100-only relay
  bound to `10.10.0.31:15432` (raw `postgres-pg:5432`) and
  `10.10.0.31:15984` (Pi5 CouchDB proxy). These ports are LAN-only, have no
  edge route, and are reachable from VM110 only after the host firewall/source
  policy is verified.
- The relay is split by transport: PostgreSQL uses the `pg-net` overlay, while
  CouchDB uses a host-network Nginx stream so the Pi5 proxy sees the approved
  VM100 source address instead of an overlay address.
- The scheduler dispatcher selects the local `databases` class only when both
  network transports are explicitly configured; otherwise it keeps the Pi5
  forced-command fallback. Rollback is therefore a configuration change.
- VM110 staging and marker directories are explicitly owned by `ubuntu`; secret
  files remain root-owned and group-readable only by the managed service group.

### Task 4: Reconcile documentation and observe

- Update `STATUS.md`, `STACK.md`, `VM100.md`, `PROXMOX.md`, `BACKLOG.md` and the backup runbook.
- Record VM110 resource headroom, scheduler ownership, rollback command and acceptance evidence.
- Observe one complete daily cycle before removing duplicate runtime files.
