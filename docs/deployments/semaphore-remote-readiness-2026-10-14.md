# Semaphore remote execution readiness

## Decision and verification plan

The VM100 runner must execute the existing database workflow using the existing
provisioner API, not direct database administrator credentials or host SSH.
Mount the existing `homelab_provisioner_token` Docker Secret read-only with
UID/GID 1001 and mode 0400. Keep the immutable runner image, private control
network, resource limits and absence of host mounts or Docker socket.

This credential permits provisioning mutations. Only trusted administrators
may edit or submit jobs to this global Community runner. It is not a tenant
security boundary. Do not enable global remote execution until template 1 uses
the GitLab source and its existing survey contract is verified.

Verification: render tests assert the exact secret, permissions and privilege
boundary; lint the installer; deploy while the runner remains inactive; inspect
the live secret metadata and check readability as UID 1001 without printing its
value. Verify the private provisioner health endpoint. A later real Semaphore
job must assert Ansible 2.18.6, not merely inspect the installed binary.

Public documentation is unchanged because this is internal controller setup.

## Verified result (2026-10-15 +07)

- Render tests: 2 passed; new secret assertion failed before implementation.
- Installer lint passed inside the pinned runner image (production profile).
  Host Python lacked PyYAML; tests used the installed Ansible Python environment.
- Installer completed: 10 OK, 5 changed, 0 failed. Only the runner stack changed;
  temporary deployment credentials were removed by the installer.
- Live runner container `337c968afb2e` on VM100 reads the nonempty secret as UID
  1001; metadata is `1001:1001 400`. No secret value was printed.
- Installed Ansible reports core 2.18.6; no Docker socket is present; provisioner
  health returns status ok over the encrypted control network.
- API reports runner 1 online and inactive. Template 1 still uses repository 1,
  inventory 1 and environment 1. Its survey names match the GitLab playbook:
  engine, database_name, application, target_environment, owner_role,
  owner_identity, policy_id and secret_ref.

Still pending: template source migration, actual remote job toolchain assertion,
global remote scheduling activation, and controlled provisioning end-to-end.
The repository branch dropdown failure is independent and remains unresolved.

## Template source migration plan

Migrate only template 1's repository ID and playbook path. Keep its ID, survey,
inventory, environment and task history. Require all tasks terminal, the exact
GitLab repository URL/branch and survey contract, and persist a private rollback
copy before PUT. Re-read and compare the preserved fields after PUT. Unknown
states or unexpected source paths fail closed. Run twice to verify idempotence.
This does not submit a provisioning task or change global runner activation.

Template 1 now uses repository 2. All editable settings were compared against
the private pre-migration copy and task history IDs 1-7 remain present. The
first post-check rejected the server-derived `last_task` projection; exclude
that projection from PUT/config comparison and verify task history separately.
Seven migration tests pass, including terminal-state and derived-field cases.

## Remote activation gate

With template 1 migrated and no jobs running, activate global runner 1 and set
`SEMAPHORE_USE_REMOTE_RUNNER=true` on the UI using stop-first rollout. Only
trusted-admin project 1 currently exists. Require `/api/info` remote mode,
runner heartbeat and a new task 2 execution reporting Ansible core 2.18.6 and
UID 1001. Do not submit a database mutation during this first execution test.
On rollout failure restore the previous UI service specification. On failed
job verification disable remote mode and deactivate runner 1 before returning
the controller to normal use.
