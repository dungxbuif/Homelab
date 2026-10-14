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
