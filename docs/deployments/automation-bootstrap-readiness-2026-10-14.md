# Automation bootstrap readiness, 2026-10-14

## Scope and intended behavior

Continue the existing automation plan without applying unverified contracts to
production. First fix inventory variable discovery and privilege defaults.
Ansible must resolve host roles and disabled mutation flags directly from the
production inventory, regardless of working directory. Read-only jobs must not
inherit global privilege escalation. Creating the automation user must not
implicitly grant root-equivalent Docker or systemctl sudo access.

Ruling: remove automatic sudo provisioning until a reviewed credential and
executor policy exists. This blocks privileged rollout rather than pretending
an unrestricted command allowlist is least privilege. Existing host sudo files
are not removed by this repository-only change.

## Verification plan

Use actual `ansible-inventory --list` output to assert resolved variables for
all three hosts. Verify all mutation defaults remain disabled and default
become is false. Test that the base role installs no sudo policy. Run inventory
contract tests and syntax checks for audit, backup audit, and bootstrap.
No SSH, service restart, route publication or VM mutation is part of this gate.

Result: four inventory-resolution tests passed; five Ruby contract tests passed
with 60 assertions. Audit, backup-audit and bootstrap syntax checks passed.
These are local validations, not a successful live Semaphore execution.

## Rollout status

Inventory resolution tests reproduced missing host roles and unsafe defaults
before the fix. Variables now live beside the inventory and match group names.
The base role no longer installs a root-equivalent sudo allowlist.

Audit commands explicitly execute in check mode and fail on command errors.
Swarm node listing runs on the manager only. Backup journal reads use an argv
command, avoiding the non-portable `pipefail` pipeline. Backup audit labels its
output as observations only, with remote snapshots and retention `not_run`;
journal markers are not proof that a Drive snapshot exists or is restorable.

Not live: Semaphore resource YAMLs remain contracts, not installed jobs.
OpenTofu import, validated execution image, live audit credentials, route/app
catalog reconciliation and end-to-end post-check/rollback remain pending.
Public app documentation is unaffected; operator instructions are internal.
