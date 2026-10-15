# Homelab Automation Control Plane Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the homelab operable through one audited automation control plane so an agent changes Git or starts an approved Semaphore job instead of opening ad-hoc SSH sessions to every host.

**Architecture:** Keep Semaphore as the private operator UI and API, Ansible as the host and service orchestrator, and OpenTofu as the Proxmox lifecycle layer. A dedicated, pinned execution environment runs jobs centrally; it may use a restricted SSH service account as a backend transport, but agents and users do not receive host credentials or control hosts directly. Runtime state remains split by responsibility: VPS public gateway, Pi5 edge/datastore/Swarm manager, VM100 production worker, and Mac-native exceptions.

**Tech Stack:** Semaphore UI, Ansible, Ansible Execution Environment, OpenTofu, Proxmox provider, GitLab repository/CI/registry, Docker Swarm and Compose, Traefik file provider, Rathole, NetBird private transport, 1Password Connect or SOPS/age, Molecule/Testinfra, ShellCheck, yamllint, Mezon notifications.

**Spec:** [`docs/deployments/runtime-inventory-2026-10-13.md`](../../deployments/runtime-inventory-2026-10-13.md), [`docs/STACK.md`](../../STACK.md), and [`docs/MAIN.md`](../../MAIN.md).

## Implementation Checkpoint: 2026-10-15

This preserves the complete approved scope. No whole-task completion is inferred
from source files, a passing unit suite, or one pilot deployment. The design and
original task checklist below remain the acceptance contract. The inventory
linked above is the dated baseline, superseded by newer observation records.

| Task | Verified progress | Required work still open |
| --- | --- | --- |
| 1: Catalog | Active/retired policies, no K8s infrastructure targets, bounded Pi/VM runtime audits | Full VPS/Mac/rootless coverage, unknown service ownership, complete cross-catalog reconciliation |
| 2: Execution image | Pinned toolchain, CI registry publication, isolated rootless CI executor | Keep actual runner digest tied to accepted CI revision; full security scan gates |
| 3: Semaphore | Source-backed templates, restricted Pi/VM observers, backup health and exact Homepage release | Viewer/Task Runner/Manager isolation, general approved plan/apply flows and notification acceptance |
| 4: OpenTofu | Observed VM baseline, import/no-destroy tests, enforced state encryption, pinned public CA and named curl/Go TLS probes | Runner mapping/trust and provider acceptance, Python strict-CA compatibility, scoped token, recoverable key escrow/backend, actual VM100 import and no-op plan |
| 5: Host baseline | VM100 Docker CE 29.8.2, encrypted overlay restored, restricted accounts enrolled on Pi/VM | VPS enrollment, all-host idempotent baseline, durable standalone overlay boot ordering |
| 6: Routes | 24 catalog routes, schema/private-gate tests, both-gateway endpoint probes | Generated live Pi/VPS publish/rollback, Stirling public ingress, private-policy/consumer reconciliation, protocol-specific checks |
| 7: Apps | Homepage digest deploy via template 6, receipt and idempotent repeat; catalog corrections | Real rollback rehearsal, other apps' build/apply boundaries, private networks, peak-resource policies, registry-pull acceptance |
| 8: DB/backup | UI provisioner, remote class snapshots, restricted health job, native local restores for uncovered PG instances | Retention terminal result/new scheduler activation, dedicated RelayHub instance enrollment, CouchLoom DB placement/coverage, remote payload restore acceptance |
| 9: Gates/drift | Policy tests, source CI, resource/route evidence and bounded release receipt | Complete automated drift/security scan, per-apply Mezon notices, full rollback artifacts |
| 10: Lockdown | Restricted pilot transport exists | Two complete Git-to-apply-to-notification acceptances, break-glass escrow and removal of general agent SSH |

Evidence index:

- [GitLab/CI publication](../../deployments/automation-gitlab-publication-2026-10-14.md)
  and [runner enrollment](../../deployments/gitlab-runner-enrollment-2026-10-14.md)
- [Homepage pilot](../../deployments/homepage-automation-release-2026-10-15.md)
- [Runtime/data reconciliation](../../deployments/runtime-catalog-reconciliation-2026-10-15.md)
- [Resource limits](../../deployments/resource-audit-2026-10-15.md)
- [Route probes](../../deployments/route-reconciliation-2026-10-15.md)
- [App deployment preflight](../../deployments/app-catalog-reconciliation-2026-10-15.md)
- [Retention prerequisite gate](../../deployments/backup-retention-ownership-2026-10-14.md)
- [Proxmox CA evidence and compatibility limits](../../deployments/proxmox-ca-trust-2026-10-15.md)

Publication checkpoint: implementation commits are on private GitLab branch
`codex/automation-bootstrap`, not merged to main. Most recent observed pipeline
states: 50/51/53 succeeded; 55/56 were still running. Those statuses are not a
claim that the newest source has passed CI. Historical dirty worktree files are
not automatically included in publication; preserve and reconcile them rather
than silently discarding or treating them as shipped.

Operational wait: retention unit PID 1133089 remains live, with successful
sampled pack reads logged through 01:46:48 UTC and the next repository check
started at 01:47:36. Do not restart it because it is slow or install the new
scheduler/instance runner over the live operation. The wait is specific to that
process, not a global blocker for unrelated work.

Webhook storage for deploy notifications is being clarified with the operator;
the candidate is a separate encrypted Semaphore Secret Variable Group scoped
to release jobs. No notification secret has been enrolled or live deploy
notification claimed yet. Public application behavior is unchanged.

## Global Constraints

- Pi5 `10.10.0.5` remains the active edge, DNS, Swarm manager, PostgreSQL/PgBouncer, Redis, RustFS, CouchDB, registry, and Semaphore/provisioner host.
- VM100 `10.10.0.31` remains the production application worker and GitLab/backup host; it is not the database host.
- The VPS remains the public Traefik/Rathole boundary; application databases and general application workloads must not move there.
- The Mac remains an explicit native-service exception for OCR/LM Studio; it is not made a general Docker target.
- The current Pi5 Traefik uses the file provider. Docker labels are metadata only until a deliberate provider migration is approved; routes remain generated file configuration.
- Agents must not receive general host SSH credentials, Docker socket access, database passwords, or plaintext secret files.
- Backend automation may use SSH only from the controlled runner, with a dedicated restricted account and short-lived or narrowly scoped credentials.
- OpenTofu manages Proxmox objects only. Ansible manages host configuration and service orchestration. Application data is never destroyed by an infrastructure plan.
- Existing production services are not stopped during bootstrap, import, check, or read-only audit phases.
- Redis and NATS remain excluded from the database backup contract.
- Existing dirty worktree changes, runtime data, backups, and historical documents must not be reverted or deleted as part of this plan.
- Every apply/deploy job must produce a plan or diff, a verification result, and a rollback reference before it reports success.

## Review Focus

- **Accidental destruction during VM import:** OpenTofu must show import-only or an explicitly approved delta for VM100 before any apply; cover with an import plan test and a no-destroy policy check in Task 4.
- **Credential leakage through jobs:** Semaphore logs, survey values, Ansible facts, and CI artifacts must contain references rather than secret values; cover with redaction tests in Tasks 2 and 3.
- **Route drift or public exposure:** generated Pi5/VPS routes must contain only declared services and no public route to Semaphore, raw PostgreSQL, Redis, or backup runners; cover with route schema and smoke tests in Task 6.
- **Partial app rollout:** a failed health check must leave the previous image/config available for rollback; cover with digest pinning and rollback tests in Task 7.
- **Automation drift:** manual host changes must be reported without being silently overwritten; cover with read-only audit output and check-mode runs in Tasks 3 and 8.

## Audit Result and Decisions

### What exists today

1. The live topology is documented in the 2026-10-13 runtime inventory. Pi5 is the active edge/datastore/Swarm manager, VM100 is the production worker, and the VPS is the public boundary.
2. Semaphore is live and private on Pi5, but currently has a narrow `db-provision` template and the private provisioner. It is not yet the control plane for host/app deployment.
3. Backup automation is the most mature automation slice: VM100 systemd timers schedule native database, GitLab, and RustFS workflows; Pi5 has a forced-command backup executor. This is a good existing pattern to preserve and generalize.
4. Kubernetes is not part of the current lab. `iac/terraform/` and `iac/ansible/` are historical placeholder Kubernetes/kube-vip material only; they must never be loaded as an active inventory or executed by a new job. If KubeKosh remains deployed, it is treated as one isolated learning application, not as a Kubernetes cluster managed by this control plane.
5. Route ownership is split between the canonical repository file `migration/traefik/dynamic.yml` and host-side VPS/Rathole configuration. There is no single structured route catalog with generated outputs and validation.
6. Secrets are split across Docker secrets, host secret files, Semaphore credentials, 1Password/local operator state, and runtime backup files. There is no one documented retrieval contract for automation jobs.
7. The broad `homelab-net` overlay remains for compatibility; several workloads already have narrower networks (`relayhub-net`, `bds-tunnel-net`, and CouchLoom's data network). The automation layer must preserve these boundaries rather than flattening them.

### Recommended tool boundary

| Tool | Owns | Must not own |
|---|---|---|
| Semaphore | Private UI/API, RBAC, approvals, job history, schedules, audit trail | The canonical service definitions or arbitrary shell access for agents |
| Ansible | OS baseline, Docker/Swarm membership, secrets installation, routes, timers, app deploy orchestration | Proxmox VM lifecycle or application data deletion |
| OpenTofu | Proxmox VM100 and explicitly approved lab VM lifecycle, state, import, resource sizing | Containers, databases, Traefik routes, or credentials |
| GitLab | Source of truth, merge review, CI checks, image registry, signed/pinned artifacts | Direct production apply without a Semaphore approval gate |
| 1Password Connect / SOPS-age | Runtime secret retrieval or encrypted secret material | Plaintext values in Git, surveys, logs, or local untracked JSON |
| NetBird | Private transport for operator/runner access when LAN is unavailable | Configuration ownership or a replacement for the route catalog |
| Native app CLIs/APIs | Consistent DB/GitLab/RustFS exports and health checks | Generic filesystem copying of live state |

Keep Semaphore rather than adding AWX, Kestra, or Atlantis now. Semaphore already supports Ansible, OpenTofu, scripts, inventories, credentials, task history, schedules, API triggers, and runners. Kubernetes execution is outside the current lab scope; add another controller only if a future non-Kubernetes requirement genuinely needs it.

## Target Control Flow

```text
User or coding agent
  -> Git commit / merge request / approved Semaphore API call
  -> Semaphore private UI/API
  -> pinned automation execution image
  -> Ansible check/plan/apply OR OpenTofu plan/apply
  -> restricted automation account over NetBird/LAN transport
  -> VPS / Pi5 / VM100 / approved Mac exception
  -> smoke tests, resource audit, route check, backup marker check
  -> task log + machine-readable report + Mezon notification
```

The important distinction is that SSH does not need to disappear from the backend. It becomes one controlled transport used by the runner, with no host keys exposed to an agent and no manual per-host command sequence. For API-only operations, the runner should call the service API directly; it must not enable Docker's unauthenticated remote API.

## Proposed Repository Layout

Create the new active automation tree without reusing the historical Kubernetes paths:

```text
automation/
  ansible/
    inventories/production/hosts.yml
    group_vars/{all,gateway,pi5,vm100}.yml
    roles/{base,docker,swarm,edge-traefik,rathole,adguard,secrets,
           backup,semaphore,provisioner,apps,observability}/
    playbooks/{bootstrap,audit,edge,datastore,worker,apps,backup,retire}.yml
    requirements.yml
  tofu/
    proxmox/{main.tf,variables.tf,outputs.tf,versions.tf,imports.tf}
  execution-environment/
    Containerfile
    ansible-builder.yml
    requirements.txt
    requirements.yml
  routes/
    catalog.yml
    schemas/route.schema.json
    generated/{pi5-traefik.yml,vps-rathole.toml}
  stacks/
    {infra,apps}/<service>/compose.yml
  policies/
    resources.yml
    approvals.yml
  scripts/
    audit-runtime.sh
    verify-routes.sh
    verify-deploy.sh
```

The current `automation/backup-runner`, `automation/semaphore`, `automation/provisioner`, and `backup/` trees remain in place during migration. Each new playbook must call or wrap an existing contract instead of silently duplicating it.

---

### Task 1: Freeze the Runtime Inventory and Retire Misleading IaC

**Files:**
- Create: `docs/superpowers/specs/2026-10-13-homelab-automation-control-plane.md`
- Create: `automation/policies/active-runtime.yaml`
- Create: `automation/policies/retired-runtime.yaml`
- Create: `automation/README.md`
- Modify: `docs/INDEX.md`, `docs/STACK.md`, `docs/MAIN.md`
- Modify: `iac/README.md`, `iac/terraform/INDEX.md`, `iac/ansible/INDEX.md`
- Preserve unchanged as history only: `iac/k8s/`, `iac/ansible/`, `iac/terraform/`

**Interfaces:**
- `active-runtime.yaml` is the machine-readable host/service/owner catalog consumed by audit and deployment jobs.
- `retired-runtime.yaml` lists Orange Pi edge services, historical Kubernetes/kube-vip resources, old Caddy/Headscale/Coturn/NetBird remnants, and other non-authoritative history.

- [ ] Copy the verified host roles, service owners, networks, image references, route exceptions, and backup classes from the runtime inventory into `active-runtime.yaml` without secrets.
- [ ] Add explicit `lifecycle: historical` metadata and a warning banner to old Kubernetes IaC docs so no new job can target them at all.
- [ ] Add a parser that fails on duplicate host/service IDs, retired targets in a production inventory, or unapproved public ports.
- [ ] Run the parser and compare its output to the 2026-10-13 runtime inventory; expected result is a report with no Kubernetes hosts, nodes, control plane, route, or resource target and no secret values.

### Task 2: Build the Pinned Automation Execution Environment

**Files:**
- Create: `automation/execution-environment/Containerfile`
- Create: `automation/execution-environment/ansible-builder.yml`
- Create: `automation/execution-environment/requirements.txt`
- Create: `automation/execution-environment/requirements.yml`
- Create: `automation/execution-environment/tests/test-toolchain.sh`
- Modify: `.gitlab-ci.yml` or create it if absent

**Interfaces:**
- Produces `registry.dungxbuif.com/homelab/automation-ee:<git-sha>` with pinned Ansible, OpenTofu, Docker CLI, validation tools, and required collections.
- The image is the only default executor image for infrastructure jobs.

- [ ] Pin versions for `ansible-core`, `community.docker`, `community.general`, the Proxmox collection/provider tooling, OpenTofu, `yamllint`, `ansible-lint`, and ShellCheck.
- [ ] Build the image in GitLab CI and publish it by immutable commit tag and digest; never use `latest` in a production job template.
- [ ] Run `ansible --version`, `tofu version`, `docker version --format`, `yamllint --version`, and `ansible-lint --version` inside the image.
- [ ] Add CI gates for YAML parsing, shell syntax, Ansible lint, OpenTofu format/validate, route schema validation, and secret-pattern scanning.

### Task 3: Make Semaphore the Only Operator Entry Point

**Files:**
- Create: `automation/semaphore/project-resources.yaml`
- Create: `automation/semaphore/templates/host-audit.yaml`
- Create: `automation/semaphore/templates/ansible-check.yaml`
- Create: `automation/semaphore/templates/ansible-apply.yaml`
- Create: `automation/semaphore/templates/tofu-plan.yaml`
- Create: `automation/semaphore/templates/tofu-apply-approved.yaml`
- Create: `automation/semaphore/templates/route-publish.yaml`
- Create: `automation/semaphore/templates/app-deploy.yaml`
- Create: `automation/semaphore/templates/rollback.yaml`
- Modify: `automation/semaphore/README.md`, `automation/semaphore/stack.yml`, `docs/STACK.md`

**Interfaces:**
- Every template declares repository revision, execution image, inventory/workspace, allowed variables, required approval, and post-check.
- `host-audit` is read-only. `ansible-check` and `tofu-plan` are non-mutating. Apply/deploy templates require an approved plan artifact or an explicit operator approval.

- [ ] Keep the UI private on LAN/NetBird and keep the provisioner portless; do not add a public route or Docker socket mount.
- [ ] Configure separate roles for `Viewer`, `Task Runner`, and `Manager`; only `Manager` can apply OpenTofu or production app changes.
- [ ] Replace free-form survey fields with enumerated targets, service IDs, image digests, and change messages.
- [ ] Configure the execution environment image and a single runner path; remove stale templates/schedules that duplicate systemd backup ownership.
- [ ] Trigger a no-op `host-audit` and verify task history, redacted logs, and Mezon failure/success behavior.

### Task 4: Bring VM100 under OpenTofu Without Recreating It

**Files:**
- Create: `automation/tofu/proxmox/versions.tf`
- Create: `automation/tofu/proxmox/providers.tf`
- Create: `automation/tofu/proxmox/main.tf`
- Create: `automation/tofu/proxmox/variables.tf`
- Create: `automation/tofu/proxmox/outputs.tf`
- Create: `automation/tofu/proxmox/imports.tf`
- Create: `automation/tofu/proxmox/README.md`
- Modify: `docs/PROXMOX.md`, `docs/VM100.md`, `docs/INDEX.md`

**Interfaces:**
- The initial workspace manages only the existing VM100 object and explicitly approved optional practice VMs.
- The state backend is private, encrypted, versioned, and separate from application data. Prefer a dedicated RustFS S3 bucket such as `iac-state` only after versioning, credentials, and recovery are verified; otherwise use an encrypted local state on the controlled runner for the import phase.

- [ ] Freeze a provider version and write the VM100 resource to match the live VM before importing.
- [ ] Add an import block or equivalent import workflow for VM ID `100`; do not model VM IDs `101`/`102` as active resources.
- [ ] Run `tofu fmt`, `tofu init`, `tofu validate`, and `tofu plan` through Semaphore with no apply.
- [ ] Require the plan to show import-only or a reviewed zero-destroy delta. Any disk replacement, network replacement, or unexpected VM recreation blocks rollout.
- [ ] After approval, apply the import and rerun `tofu plan`; the second plan must be no-op before resource sizing changes are considered.
- [ ] Manage CPU/RAM/disk/swap as explicit variables only after the imported baseline is stable.

### Task 5: Replace the Placeholder Inventory with Ansible Host Baseline

**Files:**
- Create: `automation/ansible/inventories/production/hosts.yml`
- Create: `automation/ansible/group_vars/all.yml`
- Create: `automation/ansible/group_vars/gateway.yml`
- Create: `automation/ansible/group_vars/pi5.yml`
- Create: `automation/ansible/group_vars/vm100.yml`
- Create: `automation/ansible/playbooks/bootstrap.yml`
- Create: `automation/ansible/playbooks/audit.yml`
- Create: `automation/ansible/roles/base/tasks/main.yml`
- Create: `automation/ansible/roles/base/handlers/main.yml`
- Create: `automation/ansible/roles/docker/tasks/main.yml`
- Create: `automation/ansible/roles/swarm/tasks/main.yml`
- Create: `automation/ansible/roles/ssh_hardening/tasks/main.yml`
- Create: `automation/ansible/roles/logging/tasks/main.yml`
- Create: `automation/ansible/roles/swap/tasks/main.yml`
- Modify: `docs/PI.md`, `docs/VM100.md`, `docs/MAIN.md`

**Interfaces:**
- Inventory groups are `gateway`, `pi5_manager`, and `vm100_worker`; no `k8s_cluster` group, Kubernetes node, kube-vip address, or Kubernetes API target exists in the production inventory.
- `audit.yml` never mutates state and returns JSON plus human-readable output for Semaphore artifacts.

- [ ] Create a dedicated `automation` account on each managed host with only the sudo rules required by the role set.
- [ ] Use NetBird/private LAN hostnames as the preferred transport and retain a separate bootstrap path for first enrollment; do not hardcode app IP endpoints.
- [ ] Load SSH credentials from Semaphore Key Store initially; design the inventory so a future SSH CA or 1Password Connect source can replace it without changing playbooks.
- [ ] Keep the existing forced-command backup key separate from the general automation account.
- [ ] Apply base roles in check mode first, then to one non-production target, then Pi5/VM100/VPS in that order.
- [ ] Verify Docker versions, Swarm membership, disk/swap/logging policy, time sync, firewall, and SSH policy without restarting production containers.

### Task 6: Generate and Validate Edge, Tunnel, and DNS Configuration

**Files:**
- Create: `automation/routes/catalog.yml`
- Create: `automation/routes/schemas/route.schema.json`
- Create: `automation/scripts/render-routes.py`
- Create: `automation/scripts/verify-routes.sh`
- Create: `automation/ansible/roles/edge-traefik/`
- Create: `automation/ansible/roles/rathole/`
- Create: `automation/ansible/roles/adguard/`
- Modify: `migration/traefik/dynamic.yml`, `docs/MAIN.md`, `docs/PI.md`, `docs/STACK.md`

**Interfaces:**
- `catalog.yml` is the only editable route list; generated Pi5 Traefik and VPS/Rathole outputs are deployment artifacts.
- Each route declares exposure (`public`, `lan`, `netbird`, `internal`), owner, backend kind (`service_dns`, `tunnel`, `mac_exception`), health path, and rollback version.

- [ ] Encode current public/private routes and explicit exceptions such as Mac LM Studio/OCR, GitLab isolated tunnels, BDS Cloudflare tunnel, and private Semaphore.
- [ ] Generate file-provider Traefik config and validate YAML, host rules, TLS resolver references, duplicate hostnames, and forbidden raw DB/Redis/backup routes.
- [ ] Generate only the Rathole listener/client fragments that are declared; do not reintroduce Caddy, Orange Pi edge services, or retired tunnels.
- [ ] Publish configs atomically with a backup, syntax validation, reload, and route smoke test; automatically restore the previous file if validation or smoke fails.
- [ ] Verify LAN split DNS and public DNS paths separately; report any route that resolves to a stale IP or bypasses the intended tunnel.

### Task 7: Standardize Swarm and Compose Application Deployment

**Files:**
- Create: `automation/stacks/catalog.yml`
- Create: `automation/stacks/infra/<service>/compose.yml`
- Create: `automation/stacks/apps/<service>/compose.yml`
- Create: `automation/ansible/roles/apps/tasks/main.yml`
- Create: `automation/scripts/verify-deploy.sh`
- Modify: existing service manifests only after catalog entry exists
- Modify: `docs/STACK.md`, `docs/VM100.md`, service runbooks

**Interfaces:**
- Each app entry declares image digest, target host/mode, private networks, published ports (normally none), secret references, route IDs, health checks, resource limits, and rollback image.
- Deploy jobs accept only a catalog service ID and an immutable image digest; they do not accept arbitrary shell or arbitrary Compose paths.

- [ ] Import the current runtime catalog one app at a time: infrastructure services, RelayHub, CouchLoom, BDS connector, GitLab, KubeKosh, Homepage, OCR proxy, MyPocket, NetBird, OpenClaw, n8n, Stirling, and remaining active workloads.
- [ ] Preserve Pi5 file-provider routing and use service DNS/`tasks.<service>` instead of hardcoded container IPs wherever the runtime boundary permits.
- [ ] Declare narrow per-app overlay networks and connect only the edge/router, app, and required datastore endpoints. Keep `homelab-net` only for legacy/shared infrastructure compatibility.
- [ ] Build images in GitLab CI, publish by digest, deploy through Semaphore, run health/smoke checks, and retain the previous digest for rollback.
- [ ] Validate `docker stack config` and `docker compose config` before any remote apply; do not publish host ports for internal services.

### Task 8: Unify Database Provisioning and Backup Operations

**Files:**
- Create: `automation/ansible/playbooks/db-provision.yml`
- Create: `automation/ansible/roles/db-provision/`
- Create: `automation/semaphore/templates/db-provision.yaml`
- Create: `automation/semaphore/templates/backup-audit.yaml`
- Modify: `automation/semaphore/playbooks/db-provision.yml`, `backup/inventory.yaml`, `docs/runbooks/db-provisioning.md`, `docs/runbooks/backup-restore.md`

**Interfaces:**
- The user-facing DB form accepts engine, safe database name, application, environment, owner identity, and backup policy. It never accepts inline passwords, SQL, or arbitrary API bodies.
- Backup schedules continue to invoke native PostgreSQL/CouchDB/GitLab/RustFS workflows; Ansible installs and verifies timers but does not replace the native export logic.

- [ ] Keep the private provisioner as the least-privilege API boundary and make Semaphore the only UI that can call it.
- [ ] Reconcile the playbook, catalog, Docker secret, and backup inventory transactionally; rerunning a request must be idempotent.
- [ ] Add a read-only backup audit job checking timers, class markers, remote snapshot IDs, retention state, stale `.incomplete` runs, and staging disk without deleting anything.
- [ ] Fix and verify the current health-timer ordering/start-time warning before claiming the backup health gate is clean.
- [ ] Keep Google Drive credentials, Restic passwords, DB credentials, and Mezon webhook values in the selected secret boundary; mask all job output.

### Task 9: Add CI Gates, Drift Reports, and Rollback

**Files:**
- Create: `automation/policies/approvals.yml`
- Create: `automation/scripts/audit-runtime.sh`
- Create: `automation/scripts/report-drift.py`
- Create: `automation/tests/test_policy_contract.py`
- Create: `automation/tests/test_route_contract.py`
- Create: `automation/tests/test_no-secret-output.sh`
- Modify: `.gitlab-ci.yml`, `docs/LOG.md`, `docs/INDEX.md`

**Interfaces:**
- `audit-runtime.sh --json` returns host/service/routes/resources/backup status without secret values.
- `report-drift.py` compares live read-only facts with `active-runtime.yaml` and exits non-zero only for declared policy violations.

- [ ] Add separate CI stages: lint, unit/policy tests, OpenTofu plan, Ansible check, route render, and package/image security scan.
- [ ] Make production apply manual and approval-gated; allow automatic applies only for explicitly classified lab resources.
- [ ] Generate a rollback artifact containing previous image digests, previous route hash, stack revision, and the exact Semaphore task ID.
- [ ] Send one sanitized Mezon notification for success/failure of each approved apply; include task ID, commit, target, and verification summary only.
- [ ] Run the full read-only audit against VPS, Pi5, VM100, and active Mac exception; publish the report as a CI/Semaphore artifact.

### Task 10: Remove Direct Agent-to-Host Operations

**Files:**
- Modify: Semaphore credentials/inventory and local agent instructions
- Create: `docs/runbooks/automation-operations.md`
- Modify: `docs/INDEX.md`, `docs/MAIN.md`, `docs/LOG.md`

**Interfaces:**
- Normal operation is: edit/merge automation code, run plan/check, approve, apply, verify.
- Break-glass operation is a separately audited administrator path, never the default agent path.

- [ ] Remove general-purpose host keys from agent-facing local configuration after two successful end-to-end runs.
- [ ] Keep one offline/break-glass administrator credential with documented rotation and recovery steps.
- [ ] Add a rule that an agent request for direct `ssh`, `scp`, Docker socket, or database credentials is rejected unless it is a documented recovery task.
- [ ] Verify a complete workflow from a Git change to Semaphore task, Ansible/OpenTofu result, smoke test, rollback reference, and Mezon notice without an agent opening a host session.

## Rollout Order and Gates

1. **Audit/freeze:** create the active machine-readable inventory, classify the old K8s IaC as historical-only, and prove that no Kubernetes target is discoverable. No runtime changes.
2. **Control plane:** build the execution environment and Semaphore resources. Prove read-only `host-audit`.
3. **OpenTofu import:** import VM100 with an import-only/no-destroy plan. Stop on any replacement or destroy action.
4. **Host baseline:** run Ansible check mode, then one host at a time: VPS, Pi5, VM100. Do not change application images yet.
5. **Routes:** generate and verify Pi5/VPS route outputs, then test LAN and public paths. Roll back on any stale IP, TLS, or private-route exposure.
6. **One app pilot:** deploy a low-risk internal app with an immutable digest and rollback check. Do not pilot on PostgreSQL, GitLab, or the edge.
7. **Data/backup:** move DB provisioning and backup health checks into the same job model, while retaining native exports and existing timers.
8. **Production apps:** migrate one service per change window, in dependency order: infrastructure networks/edge, data clients, RelayHub/CouchLoom/BDS, GitLab, then remaining apps.
9. **Lockdown:** remove agent-facing general SSH access, retain break-glass, and make CI/Semaphore the documented operating path.

## Definition of Done

- A fresh operator can view the active system in `active-runtime.yaml` and identify host, service, network, route, secret reference, resource policy, and rollback version; Kubernetes is absent from that inventory.
- An agent can propose and verify changes through Git/Semaphore without receiving a general host SSH key or entering a host shell.
- `tofu plan` is the only path that changes Proxmox VM lifecycle, and VM100 is imported with no unexpected destroy/recreate.
- Ansible check/apply is idempotent on VPS, Pi5, and VM100, with separate inventories and least-privilege credentials.
- Every active route is generated from a catalog and passes public/LAN/private smoke checks.
- Every deployed app uses an immutable image reference, declared private networks, resource limits, health check, and rollback artifact.
- DB provisioning remains UI-driven and idempotent; backup scheduling remains native and its health is visible in the same control plane.
- A read-only audit reports drift, open ports, hardcoded IP endpoints, failed timers, stale images, and resource pressure without mutating production.
- The user-facing docs explain the operator workflow and the machine-readable catalog/contract is available to automation jobs.

## References

- [Semaphore task templates and inventories](https://semaphoreui.com/docs/user-guide/task-templates)
- [Semaphore applications and OpenTofu support](https://semaphoreui.com/docs/user-guide/apps)
- [Semaphore getting started and runners](https://semaphoreui.com/docs/getting-started)
- [Ansible Execution Environments](https://docs.ansible.com/projects/ansible/latest/collections/community/general/docsite/guide_ee.html)
- [OpenTofu import](https://opentofu.org/docs/cli/commands/import/)
- [OpenTofu state](https://opentofu.org/docs/language/state/)
- [1Password Connect server configuration](https://www.1password.dev/connect/server-configuration/)
