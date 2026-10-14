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

## Evidence

- https://semaphoreui.com/docs/user-guide/task-templates
- https://semaphoreui.com/docs/admin-guide/runners
- https://github.com/semaphoreui/semaphore/blob/v2.19.12/api/runners.go
- https://github.com/semaphoreui/semaphore/blob/v2.19.12/cli/cmd/runner_start.go
