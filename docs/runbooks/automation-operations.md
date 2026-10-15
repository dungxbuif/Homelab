---
type: Runbook
title: "Homelab automation operations"
description: "Safe operator workflow for audit, plan, approval, apply, verification, and rollback"
timestamp: 2026-10-15T00:00:00+07:00
---

# Homelab automation operations

## Implementation status, 2026-10-15

The full flow below is still a target, but seven live Semaphore templates now
exist. GitLab CI/registry publication, restricted Pi5/VM100 observers, backup
health, a fixed-digest Homepage release, and the Homepage Mezon deployment
notification boundary are installed. VM100 OpenTofu import, general route/app
apply and full RBAC remain incomplete.
Do not execute arbitrary declarative apply templates as though they were enrolled.
The project currently has one owner membership; separate Viewer/Task Runner/
Manager permissions have not been proven. Backup health reports state and
markers; it does not independently restore Drive payloads.

Do not grant `task_runner` in this mixed project merely to allow audits: that
built-in role can run its mutating templates too. The proposed separate audit
project and its denial-test requirements are recorded in the
[RBAC boundary review](../research/semaphore-rbac-boundary-2026-10-15.md), pending
operator choice. No fine-grained authorization has been enabled by this document.

## What you can run in the UI

Open [Semaphore project 1](https://semaphore.dungxbuif.com/project/1/templates)
from your approved LAN/NetBird access path. Select the exact template below,
start a task and inspect its output. Keep the task ID when reporting an issue.

| Template | Purpose and boundary |
| --- | --- |
| [1: Provision database and application owner](https://semaphore.dungxbuif.com/project/1/templates/1) | Creates a DB and owner, generates its secret and enrolls it in the backup catalog; this changes state. Follow the DB provisioning runbook. |
| [2: Verify GitLab source and control connectivity](https://semaphore.dungxbuif.com/project/1/templates/2) | Checks the source/control path, not every app or backup. |
| [3: Check backup health (read only)](https://semaphore.dungxbuif.com/project/1/templates/3) | Checks backup state; it does not start a backup, retention or restore. |
| [4: Inspect VM100 runtime (read only)](https://semaphore.dungxbuif.com/project/1/templates/4) | Collects rootful Docker, networks, listeners and resource observations. |
| [5: Inspect Pi5 runtime (read only)](https://semaphore.dungxbuif.com/project/1/templates/5) | The equivalent Pi5 observation. |
| [6: Release approved Homepage](https://semaphore.dungxbuif.com/project/1/templates/6) | Applies only the exact root-approved Homepage digest. It is not a generic deploy form or arbitrary-image input. |
| [7: Release backup client (Pi5)](https://semaphore.dungxbuif.com/project/1/templates/7) | Installs the reviewed five-file backup runtime bundle under the Pi5 backup lock. It is Pi5-only, requires explicit release approval, and is not an application deployer. |

Templates 3/4/5 require no application passwords or survey values. A successful
host audit means its declared collection completed, not that every application
works. Tasks 49/50 are the latest successful VM100/Pi5 collection checkpoint.
Rootless CI,
VPS and Mac are not included by those host observers. A failed audit must be
investigated rather than rerun until a green result conceals missing coverage.

The generic source template `host-audit` is intentionally `design_only`: it
uses the production transport inventory, while the restricted observer
playbook requires a per-host dynamic inventory and a forced `host-audit`
command. The enrolled VM100/Pi5 observer templates created by
`bootstrap-host-audit.mjs` are the authoritative audit path; do not re-enable
the generic template without reconciling that inventory and evidence contract.

Backup schedules remain systemd timers on VM100. Adding a DB through template
1 enrolls it for the next database run; it does not start an immediate upload.
The guarded retention scheduler is installed. The newly enrolled dedicated
RelayHub instance has a successful native VM100 backup and remote snapshot
post-check; remote Drive restore acceptance remains a separate bounded gate.
Homepage template 6 sends its validated receipt through a dedicated secret
Variable Group; task 56 is the live notification acceptance record.
Backup-client template 7 completed live task 65. The Pi5 canonical database
payload verifier then passed its full local source-run check for 29 artifacts
and 6,915,289,967 bytes. The separate targeted remote PostgreSQL rehearsal
passed, while full remote restore acceptance remains open.

The target normal change path is GitLab change -> Semaphore check/plan -> approved
apply -> post-check -> sanitized Mezon notice. An agent does not open a host
shell, receive a general host key, mount the Docker socket, or receive a
database credential.

## Read-only checks

Run these in the pinned execution environment:

```bash
automation/scripts/audit-runtime.sh --json
automation/scripts/verify-routes.sh
ansible-playbook automation/ansible/playbooks/audit.yml --syntax-check
ansible-playbook automation/ansible/playbooks/backup-audit.yml --syntax-check
```

The declarative audit returns `status: not_verified`, reports the active policy and marks live transport,
resources, and backup observations as `not_run` until Semaphore executes the
host audit with its restricted credential. This prevents a local Git checkout
from being mistaken for proof of live health.

`report-drift.py` rejects declarative, incomplete or older-than-15-minute
observations (exit 2). A successful comparison only proves inventory IDs
match; it does not certify service health, resource capacity or backups.
The complete cross-host inventory collector remains pending. See
`docs/deployments/runtime-audit-evidence-2026-10-14.md` for its input contract.

The host audit can now save partial host evidence using
`-e audit_artifact_dir=/path/to/private/artifacts`. It writes per-host JSON
on the controller (0700 directory, 0600 files), not on the production host.
These `host_runtime_only` records contain safe container/network summaries and
a resource sample; they must not be fed directly into the full drift gate.
Pi5 and VM100 now have restricted controller credentials and live Semaphore
templates. Bootstrap administration is still used for unenrolled operations;
general agent SSH has not been removed. Complete route/backup/remote-host
collection remains pending.

## Change gates

1. Edit the catalog or playbook in Git and run CI lint/policy tests.
2. Run `host-audit`, then `ansible-check` or `tofu-plan`.
3. Review the plan artifact. OpenTofu VM100 plans must be import-only or
   zero-destroy; application changes must use an immutable image digest.
4. The target policy requires a Manager to approve mutating templates; that
   separated role flow is not deployed yet. Route publication needs LAN and
   public smoke checks; application changes need a health check and rollback
   reference.
5. Keep the task ID, commit, previous image/route hash, and post-check artifact
   as the rollback record.

## Current limits

### Image security before publication

New automation builds run a pinned Trivy scan before pushing each EE, runner or
arm64 provisioner image. Open the build job's `security-reports/` artifact to
inspect HIGH/CRITICAL findings. Reports are retained for 14 days, including
failed jobs. Scanner errors and end-of-life OS also fail the gate; a failed
scan does not stop an already running application or authorize an upgrade.

Fix the affected dependency/base image and rerun CI. Do not bypass the gate with
`allow_failure`, an ignore file or `--ignore-unfixed` to obtain a green pipeline.
See the [security gate record](../deployments/automation-image-security-2026-10-15.md)
for pinned version, tests and the current rollout status. Passing this scan is
not proof of complete system security or permission to deploy without approval.

The active production inventory has `vps-gateway`, `pi5`, and `vm100` host
roles plus the explicit Mac-native dependency exception. Kubernetes is not an
active lab target. KubeKosh is a LAN-only learning application and is not a
Kubernetes cluster managed by this control plane.

The route and application catalogs are contracts first. A generated route is
not live until it is smoke-tested and atomically published. An observed app
whose registry digest is not reconciled remains `deployable: false`.

Break-glass administration remains a separately audited recovery path. It is
not the default route for an agent or a routine deployment.
