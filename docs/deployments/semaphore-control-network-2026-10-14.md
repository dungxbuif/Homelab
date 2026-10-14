# Semaphore control network migration

## Current state after approved Docker upgrade

VM100 is now Docker CE 29.8.2. The real VM100 runner can reach the private Pi
provisioner health endpoint over homelab-control-net (200, status ok). GitLab
and registry HTTPS recovered and CI runner is online/unpaused. The historical
maintenance gate and failed probes below are retained as incident evidence,
not current blockers. See `vm100-docker-upgrade-2026-10-14.md`.

Proceed with stage 4: stop-first UI rollout to control network and LAN DNS,
preserving SQLite, task history, old provisioning template, credentials and
volumes. Use service update for only network/DNS/order changes, not wholesale
stack redeployment; service rollback on failed HTTPS probe. Recheck repository
branch discovery and task history. Remote execution stays disabled for now.

### Stage 4 execution result

UI migration succeeded with stop-first and explicit DNS 10.10.0.5, retaining
all mounts/secrets. Admin login, tasks 1-6 and template 1 remain intact.
Its actual container now resolves GitLab to 10.10.0.5 and validates HTTPS with
HTTP 200. The first attempt rolled back because the Pi host's own resolver sent
the probe to a different TLS endpoint. The corrected probe uses curl --resolve
to select LAN ingress while retaining hostname/SNI/certificate verification;
the second rollout passed (`ok=5 changed=1 failed=0`).

Repository 2 branch discovery still returns HTTP 400. Server log identifies
git exit status 128. This is no longer attributable to overlay/DNS: direct
unauthenticated git reaches GitLab and correctly requests credentials. Inspection
of upstream v2.19.12 CmdGitClient/GetGitURL and key installation suggests branch
discovery may construct its HTTPS URL before decrypting the login/password key.
This is a working hypothesis, not a verified fix. Next verify an authenticated
read-only task checkout before choosing a supported upstream remedy. Never put
the token into a plaintext repository URL or disable TLS to bypass this issue.
Provisioner remains dual-attached and remote jobs remain disabled/inactive.

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

Next diagnostic: VM100 capture confirms ESP packets with SPI 0x07c31de9 leave
eth0 toward Pi5, but no return traffic is observed. Read Pi5 IPsec policy (not
state/key dumps) with the existing credential via explicit sudo stdin, keeping
credential-bearing tasks `no_log`. This tests whether the earlier failure was
Ansible prompt handling rather than missing authorization; do not change sudo
policy, PAM or credentials to work around it.

## Root cause confirmed

Pi5 runs Docker CE 28.4.0; VM100 runs Ubuntu docker.io 29.1.3. The outgoing SPI
on VM100 is 0x07c31de9, while Pi5 has no matching inbound association (its three
inbound SPIs are 0x3e402bd0, 0x76910f83 and 0x18113769). Likewise Pi5's outgoing
SPI differs from VM100's inbound associations. This matches upstream
[Moby 51798](https://github.com/moby/moby/issues/51798), fixed by
[51951](https://github.com/moby/moby/pull/51951): IPv4 hash inputs changed from
16-byte to 4-byte form, so engines derived incompatible SPIs.
The [29.2.1 release notes](https://docs.docker.com/engine/release-notes/29/#2921)
document restored compatibility with v28 engines. DNS is working; firewall
guessing, XFRM key edits and disabling TLS/encryption are not the remedy.

Explicit sudo stdin with the existing login password succeeded on Pi5 without
changing permissions or authentication configuration. Earlier Ansible escalation
was a prompt-handling failure, not proof the user lacked sudo access. Diagnostics
use `nokeys`, per the [ip-xfrm manual](https://man7.org/linux/man-pages/man8/ip-xfrm.8.html).

## Maintenance gate

An asynchronous approval question has been sent for a controlled Docker upgrade
and restart on VM100. No upgrade or daemon restart has been performed. Current
APT metadata offers only docker.io 29.1.3; docker-ce has no configured candidate.
Do not run a blind `apt upgrade`, change repositories or replace containerd yet.

Before any approved upgrade: determine a supported patched package source and
exact version; simulate dependencies/removals; record production and rootless CI
daemon configs and all service/image/mount states; pause CI when idle; prepare
a tested recovery path including VM/storage snapshot where supported. Preserve
/var/lib/docker and /var/lib/containerd, existing Swarm membership and all data.
Restart only under the approved maintenance window, then verify service health,
encrypted cross-node provisioner traffic, CI and private registry before moving
Semaphore UI. A fallback package install alone is not proof data-format rollback
is safe. The original broader automation plan remains incomplete.
