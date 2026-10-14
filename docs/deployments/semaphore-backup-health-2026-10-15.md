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
