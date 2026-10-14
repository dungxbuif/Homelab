# VM100 controlled Docker upgrade

User approved Docker upgrade and a controlled restart on 2026-10-14.
Current Ubuntu Jammy docker.io is 29.1.3, with containerd 2.2.1 and runc 1.3.4.
Pi is Docker CE 28.4.0. Encrypted overlay SPI incompatibility is confirmed in
the control-network deployment note. Fix requires Docker >=29.2.1.

## Plan and gates

1. Finish active CI before stopping its rootless daemon; pause runner enrollment
   to avoid new jobs during package transition. Record active production containers.
2. Add official signed Docker apt repository, inspect exact package candidates,
   simulate replacement of Ubuntu docker.io/containerd/runc, and download old
   packages for rollback. No autoremove/purge and no Docker data deletion.
3. Check Proxmox storage, create a named VM100 pre-upgrade disk snapshot and
   confirm completion. Snapshot is a short-lived rollback aid, not a DB backup;
   automatic rollback would lose writes after snapshot and is forbidden.
4. Install explicit tested Docker CE version and compatible containerd.io;
   retain existing Docker data root and image-store mode. Restart only as needed.
5. Verify container/service health and HTTPS routes, CI daemon, and cross-node
   encrypted control-network access. Resume runner and perform an actual job.
6. Record exact versions, snapshot name, package simulation and checks. Keep
   rollback checkpoint until all post-checks pass and user retention is resolved.

Proxmox local-lvm has ~201 GiB free at preflight; VM100 has no existing snapshot.
Docker data root /var/lib/docker uses overlayfs/containerd image store and
live-restore is false. Do not switch to overlay2 or reset Swarm membership.

Sources: https://docs.docker.com/engine/install/ubuntu/ and
https://docs.docker.com/engine/release-notes/29/ . Official installation replaces
conflicting Ubuntu packages without deleting /var/lib/docker.
Public app docs are unchanged; this is internal maintenance.

## Execution record

- Approved by user; GitLab runner 1 paused after running validation job 16
  completed successfully. No job was killed for maintenance.
- Proxmox snapshot `pre-docker-ce-20261014` completed with task exitstatus OK.
- Old packages/config/container inventory saved under root-only
  `/var/backups/homelab/docker-pre-ce-20261014` (~91 MiB initially).
- Installed Docker CE/CLI/rootless-extras 29.8.2, containerd.io 2.2.6,
  buildx 0.38.0, Compose 5.6.0. Rootful and rootless daemons report 29.8.2;
  rootful image store remains overlayfs, Swarm node identity is retained.
- First apt install hit a file collision with Ubuntu docker-compose-v2 2.40.3.
  Simulation did not detect the undeclared conflict. Removed that package only,
  completed pinned install, and confirmed `dpkg --audit` has no findings.
- Docker's old socket activation state failed on first CE start. Stopped both
  docker.service/docker.socket and started the new pair; daemon then recovered.
  The playbook now removes the conflicting Compose package before transition
  and explicitly stops both units, suppresses package autostart, then starts
  the new socket/service. Those revised ordering steps were linted but were
  not replayed against an already upgraded host.
- Four previously running standalone containers (couchloom, relayhub-api,
  kubekosh, bds-app) raced overlay startup and exited with network-not-found.
  Started those exact containers once the overlay existed; all returned running.
- VM100 runner -> Pi provisioner over encrypted homelab-control-net now returns
  HTTP 200 with status ok. This was the original failing cross-node path.
- Homepage, RelayHub, n8n, k8s-syntax, Semaphore and OpenClaw returned HTTPS 200.
  GitLab became Docker-healthy after Rails startup, then HTTPS sign-in returned
  200 and the registry /v2/ endpoint returned its expected 401 challenge.
  Runner 1 is unpaused again; a post-upgrade job is still to be verified.

Do not roll back the VM snapshot automatically: it predates new application
writes. Keep it as an emergency checkpoint until post-checks and retention review.
