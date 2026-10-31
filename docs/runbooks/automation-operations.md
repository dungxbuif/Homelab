---
type: Runbook
title: "Homelab automation operations"
description: "Safe operator workflow for audit, plan, approval, apply, verification, and rollback"
timestamp: 2026-10-31T00:00:00+07:00
---

# Homelab automation operations

## Current state

Semaphore (Pi5 Swarm service `semaphore` v2.19.17, private executor
`semaphore-executor_runner`) has seven live templates in project 1 and a
read-only, owner-only audit project 2. Only the templates below are real; the
files in `homelab-ops/automation/semaphore/specs/` (`ansible-check`,
`ansible-apply`, `tofu-plan`, `tofu-apply-approved`, `route-publish`,
`backup-audit`, `app-deploy`, `rollback`) are design-only — Semaphore
Community cannot enforce their approval gates or roles, and some reference
scripts that do not exist. Run apply-type changes through reviewed CI/CLI.

Limits: one owner membership, no separated Viewer/Task Runner/Manager flow, no
fine-grained RBAC. Do not grant `task_runner` in project 1 just to allow
audits — that role can also run the mutating templates. Template configuration
is UI-managed; nothing pushes templates from Git yet. The replacement design is
the [Lab IaC automation rebuild plan](../superpowers/plans/2026-10-31-lab-iac-automation-rebuild.md).

## Templates (project 1)

Open `https://semaphore.dungxbuif.com/project/1/templates` from LAN or NetBird.

| # | Template | Boundary |
| --- | --- | --- |
| 1 | Provision database and application owner | Mutating. Creates DB + owner, Swarm secret, catalog entry. See [DB provisioning](db-provisioning.md). |
| 2 | Verify GitLab source and control connectivity | Source/control path only. |
| 3 | Check backup health (read only) | Reports markers/locks; starts nothing. Meaningless while VM100 backup timers are absent. |
| 4 | Inspect VM100 runtime (read only) | Docker, networks, listeners, resources. |
| 5 | Inspect Pi5 runtime (read only) | Same for Pi5. |
| 6 | Release approved Homepage | Applies only the root-approved Homepage digest; sends a Mezon receipt. |
| 7 | Release backup client (Pi5) | Installs the reviewed five-file backup runtime bundle under the Pi5 backup lock; approval-gated. Source contract `automation/semaphore/templates/backup-client-release.yaml`. |

A green host audit (4/5) means collection completed, not that every app works.
VPS, Mac, VM110 and rootless CI are not covered. Investigate a failed audit;
do not rerun until green.

## Read-only checks (pinned execution environment, `homelab-ops`)

```bash
automation/scripts/audit-runtime.sh --json
automation/scripts/verify-routes.sh
ansible-playbook automation/ansible/playbooks/audit.yml --syntax-check
ansible-playbook automation/ansible/playbooks/backup-audit.yml --syntax-check
```

The declarative audit returns `status: not_verified` and marks live
observations `not_run` — a checkout is never proof of live health.
`report-drift.py` rejects declarative, incomplete or >15-minute-old
observations (exit 2); a pass only proves inventory IDs match. The host audit
can save per-host JSON with `-e audit_artifact_dir=/path` (controller-side,
0700/0600); these `host_runtime_only` records must not feed the full drift gate.
Scripts use `python3` from the EE; tests may set `PYTHON_BIN`.

## Change gates

1. Edit the catalog/playbook in Git; CI lint, policy and secret scan pass.
   CI discovers tests (`python -m unittest discover` plus `test_*.sh|rb`).
2. Run templates 4/5, then the Ansible check or OpenTofu plan as a reviewed
   local/CI step.
3. OpenTofu: `vm_name` explicit; executor injects the Proxmox token, state
   passphrase and CA file. Review the plan bundle (binary `vm100.tfplan`,
   text, JSON, SHA-256, manifest). VM100 plans must be import-only or
   zero-destroy; the approved apply refuses a mismatched plan ID/hash.
4. App changes use an immutable image digest, a health check and a rollback
   reference. Route changes need LAN and public smoke checks.
5. Keep commit, task ID, previous image/route hash and post-check artifact as
   the rollback record.

## Image security gate

Automation image builds (EE, runner, arm64 provisioner) run a pinned Trivy scan
before push; reports are in the job's `security-reports/` artifact (14 days).
HIGH/CRITICAL, scanner errors and EOL bases fail the job. Fix and rerun; never
bypass with `allow_failure`, ignore files or `--ignore-unfixed`.

## Break-glass workstation recovery

Only when Semaphore and the approved path cannot operate. Never put a key,
password or token in this runbook, Git, a command line or a URL.

1. Unlock 1Password and approve the SSH signing prompt for the specific host
   key only.
2. Check the agent without printing secrets:
   `ssh-add -L` and `ssh -G pi | grep -E '^(hostname|user|identityagent|identityfile|identitiesonly) '`.
   On this Linux workstation the agent socket is `~/.1password/agent.sock`
   (the `gateway` alias in `~/.ssh/config` points at a macOS socket path).
   Empty output or signing timeouts mean repair 1Password; do not loop.
3. Verify the pinned host key: `ssh-keygen -F 10.10.0.5` (Pi5),
   `ssh-keygen -F 10.10.0.31` (VM100), the `gateway` alias for the VPS. A
   changed key is a stop condition.
4. Start with an identity-only read command via `pi`, `vm100` or `gateway`.
   Record host, UTC time, reason, command and output in a private incident note.
5. For an approved mutation: snapshot config/data, run one bounded command,
   run app/route/backup post-checks, keep the rollback path with the note.
6. Close the access and return to the GitLab → Semaphore path.
