# Semaphore control network migration

## Reason and boundaries

Docker DNS on homelab-net resolves GitLab's public hostname to the GitLab
container address because its container hostname equals its external domain.
That container has no HTTPS listener, so Semaphore cannot clone over HTTPS.
Do not rename/restart GitLab or bypass TLS. Isolate automation dependencies on
an attachable encrypted overlay `homelab-control-net`, with AdGuard 10.10.0.5 as
their resolver. Public names then resolve through LAN DNS instead of Docker's
GitLab hostname entry. Keep provisioner private and use its service DNS name.

## Stages

1. Verify no Semaphore task is running (tasks 1-6 are terminal at preflight).
2. Create encrypted overlay; attach the standalone Pi5 Traefik container without
   restart. Attach provisioner while retaining its existing network temporarily.
3. Move inactive runner to the new network and verify heartbeat, HTTPS GitLab,
   and private provisioner health from VM100 before moving the UI.
4. Move Semaphore UI to the new network, with stop-first rollout for SQLite.
   Verify HTTPS UI, repository branch discovery, old template and history.
5. Remove provisioner's old network only after callers are accounted for. Persist
   source manifests and the Traefik network bootstrap so recreation is recoverable.

Rollback: reconnect the affected service to homelab-net using the saved original
network aliases and remove the new network from that service. Keep both networks
on Traefik/provisioner until UI verification passes. Never delete SQLite, secrets,
local playbooks or task history. No public documentation changes are needed.

Do not enable remote jobs during this network change. Expected verification is
runtime connectivity from containers, not just parsed YAML or network existence.

## Verified checkpoint

Network creation, Traefik attachment and provisioner dual attachment succeeded
(`ok=9 changed=3 failed=0`). The inactive VM100 runner is now only on the control
network; HTTPS GitLab sign-in returns 200 from its actual container. This removes
the GitLab hostname collision for that runner without changing GitLab itself.

Cross-node provisioner health is not yet working: runner DNS resolves the new VIP
10.0.7.4 and task address 10.0.7.5, but HTTP times out after 15 seconds. VM100 UFW
is inactive. Pi5's root-network XFRM counter shows `XfrmInNoStates=4`; this is a
diagnostic lead, not an established root cause. Pi5 system journal is not readable
by the bootstrap user, and its sudo escalation timed out. Do not remove encryption
or declare the network ready merely because Docker created it successfully.

Semaphore UI has NOT moved, and the existing provisioning path remains on
homelab-net. Provisioner retains both networks until the new path is verified.
No jobs have been activated on the new runner. Continue with encrypted overlay
diagnostics before stages 4-5; preserve the currently working path.
