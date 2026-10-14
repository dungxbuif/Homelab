---
type: Runbook
title: "Homelab automation operations"
description: "Safe operator workflow for audit, plan, approval, apply, verification, and rollback"
timestamp: 2026-10-14T00:00:00+07:00
---

# Homelab automation operations

## Implementation status, 2026-10-14

The flow below is the target, not an installed end-to-end control plane.
Semaphore templates are declarative contracts; privileged enrollment, image
validation/publication, API resource import, live audit artifacts, and VM100
OpenTofu import are still pending. Do not run production apply from these files.
Inventory loading and read-only command execution have local regression tests.
The baseline no longer grants broad Docker/systemctl sudo access. Audit command
errors now fail the task instead of being silently reported as empty output.
Backup audit only collects observations; it does not verify Drive snapshots.

The normal change path is GitLab change -> Semaphore check/plan -> approved
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
The observed inventory collector remains pending. See
`docs/deployments/runtime-audit-evidence-2026-10-14.md` for its input contract.

The host audit can now save partial host evidence using
`-e audit_artifact_dir=/path/to/private/artifacts`. It writes per-host JSON
on the controller (0700 directory, 0600 files), not on the production host.
These `host_runtime_only` records contain safe container/network summaries and
a resource sample; they must not be fed directly into the full drift gate.
Pi5 and VM100 were tested with temporary bootstrap credentials; controller
credential enrollment and complete route/backup collection are still pending.

## Change gates

1. Edit the catalog or playbook in Git and run CI lint/policy tests.
2. Run `host-audit`, then `ansible-check` or `tofu-plan`.
3. Review the plan artifact. OpenTofu VM100 plans must be import-only or
   zero-destroy; application changes must use an immutable image digest.
4. A Manager approves mutating templates. Route publication needs LAN and
   public smoke checks; application changes need a health check and rollback
   reference.
5. Keep the task ID, commit, previous image/route hash, and post-check artifact
   as the rollback record.

## Current limits

The active production inventory has `vps-gateway`, `pi5`, and `vm100` host
roles plus the explicit Mac-native dependency exception. Kubernetes is not an
active lab target. KubeKosh is a LAN-only learning application and is not a
Kubernetes cluster managed by this control plane.

The route and application catalogs are contracts first. A generated route is
not live until it is smoke-tested and atomically published. An observed app
whose registry digest is not reconciled remains `deployable: false`.

Break-glass administration remains a separately audited recovery path. It is
not the default route for an agent or a routine deployment.
