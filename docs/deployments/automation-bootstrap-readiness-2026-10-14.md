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

## Execution image gate

The existing local image successfully runs `--run`, but its default command
fails because it tries to inspect source files absent from the image. Set its
default command to the actual runtime toolchain check and run inventory tests
inside that same image. CI must explicitly load the Ansible config. Build and
test the image before any registry publication; a registry manifest digest,
not a Docker local image ID, will be the executor reference.

Semaphore `/api/ping` returned `pong` on 2026-10-14. This confirms reachability
only, not authentication or installation of new automation jobs.

Subsequent authenticated API inspection confirmed project 1, one existing
database-provisioning template, one local-file repository, localhost inventory,
and a `none` key. No host audit credential or new automation template is installed.
Credentials were loaded from the existing local protected file without printing
them. The existing provisioning job was not modified.

The rebuilt arm64 local image now passes its default runtime check. Inside the
image, four inventory-resolution tests, three policy tests, three route tests,
and the source toolchain contract passed. Ansible lint passed on 23 files with
zero reported failures/warnings (dependency deprecation messages remain).
The image has NOT been published, verified on amd64, or run as a Semaphore job.
The GitLab CI pipeline itself has NOT run; local checks do not substitute for it.

Semaphore catalog references now use the verified account namespace `dungxbuif`
and an explicit SSH `git` user. Three template contract tests passed with 143
assertions. These are internal contracts, not proof of Semaphore API compatibility.

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
