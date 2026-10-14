# Semaphore Community execution boundary

## Verified state

Installed server API reports v2.19.12, `use_remote_runner=false`, no global
runners, and `docker_executor=false`, `project_runners=false`. Existing project
1 still provisions databases through its local file repository on Pi5.

The planned YAML `execution_image` fields are intent, not native Semaphore API
configuration. Per-template Docker execution requires Pro; do not claim these
contracts enforce pinned images, role approvals, or runner placement today.

## Decision and migration gate

Use a global Community remote runner with the local executor inside a pinned
execution container on VM100. It must not receive a production Docker socket.
Pin the entire runner image, not an unsupported per-template executor field.
Validate its binary and API contract against the installed server version.

Do not enable remote-only execution until the existing provisioning job's
repository, endpoint access and secret delivery work from that runner. Enabling
it early can strand the current working UI workflow. Preserve project 1, history,
template IDs and a rollback to the local executor. First run read-only smoke
tasks, then a controlled provisioning verification before removing local mode.

This is a recorded design correction, not a deployed runner. API bootstrap token
remains temporary. Public app documentation is unaffected.

## Runner image implementation

Build a separate image from the tested execution image, copying only the static
Semaphore binary from upstream v2.19.12 index digest
`sha256:3996804607ebb63690528185bb9adc3507ee896851098e4453975f2ce7f8b435`.
Run UID/GID 1001, retain the pinned toolchain, and read runner configuration from
`/run/secrets/semaphore_runner_config`. Do not embed tokens or copy upstream SSH
configuration (which disables strict host key checking). Verify version, runner
CLI, Ansible and non-root identity before publishing. Runtime enrollment and
network/provisioning tests remain separate deployment gates.

Local ARM64 build verified: binary reports `v2.19.12-012ed06-1788086368`,
Ansible reports `2.18.6`, UID is 1001, work directories are writable and no
Docker socket is present. CI will run the same test against AMD64 before pushing
`semaphore-runner:$CI_COMMIT_SHA`. Runner ID 1 is now enrolled but inactive;
no runner container has been deployed and remote execution remains disabled.

## Enrollment procedure

Add an idempotent API enrollment command for one global runner named
`vm100-homelab-automation`. It creates the runner inactive with concurrency one,
without enabling remote execution on the server. Save its token only in ignored
`credentials/semaphore-runner.json` with mode 0600. Refuse duplicate names,
missing/mismatched saved credentials, or ambiguous previous creation attempts.
Never regenerate an existing runner token automatically. Dry-run is the default;
`--apply` is required to create. Verify repeat enrollment returns the same ID and
that the live provisioning template remains untouched.

Verified enrollment on 2026-10-14: first apply created ID 1 inactive, second
apply reused ID 1. Four Node tests cover dry-run, protected file permissions,
inactive creation/reuse, ambiguous outcomes and missing credentials. The existing
provisioning template is still ID 1, repository 1, `playbooks/db-provision.yml`.

## Sources

- https://semaphoreui.com/docs/user-guide/task-templates
- https://semaphoreui.com/docs/admin-guide/runners
- https://github.com/semaphoreui/semaphore/blob/v2.19.12/api/runners.go
- https://github.com/semaphoreui/semaphore/blob/v2.19.12/cli/cmd/runner_start.go
