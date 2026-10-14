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

The runner is deployed but inactive; migration gates remain outstanding. API
bootstrap token remains temporary. Public app documentation is unaffected.

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
the runner container is deployed on VM100 and remote execution remains disabled.

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

## Deployment preparation

Use a project-scoped GitLab deploy token with `read_registry` only for Swarm
image pulls. Keep it in ignored `credentials/gitlab-automation-registry.json`,
mode 0600; never use the administrator API token as a registry pull credential.
The manager deployment must consume a digest verified through the registry API,
create an immutable runner-config Swarm secret, and place one runner on VM100.
No published ports, host mounts, Docker socket, or host network. Start with
1 CPU / 1 GiB, concurrency one, JSON logs limited to 10 MiB x 3 files. Use the
existing homelab overlay for the provisioning dependency during transition.
Do not enable server remote execution or activate the API runner in this step.

Bootstrap registry credential creation and manager deployment remain explicit
one-time transport exceptions. Subsequent workflow execution belongs to the
controller; this does not authorize broad shell access from job containers.

Preparation verified: deploy token ID 1 has only `read_registry` and expires
2027-01-14. The runner-stack security contract, Ansible syntax check, and
Ansible lint pass locally. `homelab-net` is attachable but has no encryption
option; retain HTTPS to the Semaphore API. Dedicated control/provisioner network
segmentation is still pending and must not be reported as complete.

Deploy using `automation/ansible/playbooks/semaphore-runner-install.yml` with
the approved digest, credential paths and explicit bootstrap flag. The playbook
targets only the Pi5 manager, creates a content-addressed Swarm config secret,
deploys `semaphore-executor_runner` on VM100 and removes its temporary registry
auth directory. A 1/1 replica post-check is only container readiness: additionally
verify API runner heartbeat and provisioner connectivity before activation.

## GitLab source migration

Create a separate project deploy token with `read_repository` only, stored in
ignored `credentials/gitlab-semaphore-source.json` mode 0600. Add a Semaphore
project access key and a new HTTPS repository referencing the automation
bootstrap branch. Do not alter repository/template 1 in this preparation step.
Verify remote branches through Semaphore's repository API, which exercises its
stored credential and network path, before migrating the provisioning template.
The final approved source must move to the protected release revision after
the full automation review; the bootstrap branch is not a production approval.

Live bootstrap found two distinct DNS faults: the shared overlay resolves
`gitlab.dungxbuif.com` to 172.30.1.95 (no HTTPS listener), while the runner resolves
the private Semaphore domain to the VPS and rejects its default TLS certificate.
Set the runner DNS resolver to Pi5 AdGuard (10.10.0.5); this is resolver config,
not an application endpoint override. Keep certificate verification enabled.
The GitLab overlay hostname collision still requires network separation before
moving the existing provisioning template. Repository 2 and access key 2 were
created, but branch discovery currently fails from the Pi5 UI container.

## Live runner checkpoint

Pipeline 4 completed successfully, including the AMD64 container smoke test.
Registry repository 4 confirms runner image digest
`sha256:157f469ffcf4fc9445b06e454143d2c555447ad61d40e18ac0f8e52bbe82e428`.
The first deployment hit a missing-secret error-string assumption before any
mutation; the playbook now lists secret names and creates only absent names.
Deployment succeeded, then DNS was corrected and reapplied while reusing the
immutable secret. API runner 1 reports `online`, `active=false`, with heartbeat
2026-10-14T16:04:13Z. Server remote execution and provisioning template 1 remain
unchanged. Temporary deployment directories were removed by the always block.
The runner-stack contract and Ansible lint pass after the correction.

`bootstrap-source.mjs --apply` created access key/repository 2, but its final
branch check fails because of the overlay DNS collision above. The deploy token
was separately verified with a successful authenticated `git ls-remote` from
Mac. Do not mistake that Mac check for successful clone from the runner/UI.

- https://semaphoreui.com/docs/user-guide/task-templates
- https://semaphoreui.com/docs/admin-guide/runners
- https://github.com/semaphoreui/semaphore/blob/v2.19.12/api/runners.go
- https://github.com/semaphoreui/semaphore/blob/v2.19.12/cli/cmd/runner_start.go
