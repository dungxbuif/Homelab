# Restricted Semaphore backup health pilot

Create a dedicated VM100 system user `homelab-audit`, not a Docker/sudo-group
member. One separate SSH key is forced through a root-owned guard accepting
exactly `backup-health`. Deny shell, arguments, forwarding, PTY and user rc.
One sudoers rule permits only a root-owned helper as `ubuntu`; the helper loads
the existing private backup environment and executes the existing combined
VM100/Pi health check without notifications. It cannot start backup/retention,
read arbitrary files, change services, or access a Docker socket.

Semaphore stores this restricted key in its encrypted key store; a dedicated
inventory uses `ansible.builtin.raw` with no facts, modules or privilege
escalation. The runner therefore needs no new host mount or Docker secret.
Pin SSH host trust using the VM host public key obtained via the existing
authenticated administrator connection, never trust a blind keyscan.

Verification: reject arbitrary SSH commands/extra arguments; test sudoers syntax;
validate key identity and permissions; run health with the restricted identity;
register a separate UI template and observe its task on the nonprivileged remote
runner. A failed health result (including known retention failure) must make the
task fail while retaining useful output. Do not widen access to make it green.
Keep existing bootstrap/admin access until the full control-plane acceptance.

This is internal operator documentation; no public application behavior changes.

## Bootstrap findings

Key 3, inventory 2 and template 3 are registered separately from DB provisioning.
The public host key was read over the already authenticated VM100 connection.
Private key material remains ignored locally and in Semaphore's key store.
Direct restricted SSH rejects `id` and returns combined health output for the
literal allowed command. Ansible lint and ShellCheck passed.

Task 15 exposed that Semaphore supplies its key through an SSH agent: disabling
IdentityAgent suppressed it. Select the exact public key with IdentityFile and
IdentitiesOnly instead, preserving strict pinned host trust. Tasks 16/17 exposed
Ansible's default PTY request, incompatible with the deliberately restricted key.
Set `ansible_ssh_use_tty: false`; a local Ansible raw test then returned complete
health evidence and the real retention failure, not the transport exit 141.
Do not enable PTY or loosen forced-command matching to accommodate the client.

## Live acceptance

Task 18 used runner 1 and commit `3c1175213db62adf11846c912e5e6f4855dfddb8`.
The forced-command operation returned exit 1 with empty stderr and full combined
VM100/Pi health output: only retention was failed, both backup locks were free,
all three marker ages were present, and Pi's local health check passed.
Ansible reported changed=0 and unreachable=0; the explicit health assertion
correctly failed. This proves restricted transport and negative health reporting,
not clean retention or full backup recovery. Tasks 15-17 remain diagnostic history.
Bootstrap registration was rerun and reused key 3, inventory 2 and template 3.

Operator: open project 1, template **Check backup health (read only)**, then Run.
No survey or password is required. A red result requires reading the reported
unit/marker failure; this template does not repair, prune or initiate backups.

## Runtime secret permission correction

Task 47 later found a permission regression: the forced health helper correctly
ran as the unprivileged `ubuntu` backup account, but
`/etc/homelab-backup/runner.env` had become `root:root 0600`, so the helper
could not load its private runtime configuration. The repair contract now keeps
the file owned by `root`, group-readable only by `ubuntu`, mode `0640`, and
leaves the Pi5 copy at its private `0600` boundary. This changes no secret
value and does not grant the `homelab-audit` account direct file access.

The Ansible playbook must be applied with its explicit runtime-config approval,
then template 3 must be rerun. A successful task is required before backup
health is considered restored; no backup or retention job is started by this
permission repair.

The permission repair was applied to VM100 with check-mode first (`ok=6,
changed=2`) and then apply (`ok=6, failed=0`). The live file is
`root:ubuntu 0640`; its secret value was not printed or changed. Task 48 then
confirmed the permission issue was fixed, but correctly remained `error` because
the Pi health leg reported `homelab-backup.lock` held by PID 3128034, the parent
of the active Restic restore (PIDs 3128100/3128133). This is an intentional
serialization condition while the restore rehearsal is active, not a reason to
remove the lock or terminate the restore. Rerun template 3 only after that
operation reaches a terminal state.

Schema reference for the encrypted Semaphore SSH key payload:
https://github.com/semaphoreui/semaphore/blob/v2.19.12/db/AccessKey.go

## Clean health acceptance

Semaphore task 57, run against the live read-only health template on
2026-10-15, completed successfully with `ok=3 changed=0 failed=0
unreachable=0`. VM100 reported `backup_lock=free` and a valid GitLab success
marker; the Pi leg reported `backup_lock=free` and valid database/RustFS success
markers. The health gate is therefore clean at this observation. This does not
replace the separate remote restore rehearsals or prove future scheduled runs.
