# Dedicated rootless CI runner

## Decision

VM100 has 15.6 GiB RAM, about 8.5 GiB available, 8 GiB swap and 52 GiB
free disk at inspection. Bootstrap a dedicated `homelab-ci` user with no sudo,
no SSH key and no production Docker group. Its own rootless Docker daemon is
managed by user systemd and uses only a Unix socket. Cap the entire user slice
at 4 GiB RAM and 200% CPU. Do not stop/reconfigure production Docker or Swarm.

GitLab Runner will later use this daemon, one job at a time, project-locked.
Job containers do not receive either host Docker socket. Only pinned rootless
DinD services may request privileged mode within the rootless executor.
This is user-namespace isolation, not VM isolation; runner jobs still share the
kernel and outbound network. No untrusted/fork jobs or general host credentials.
Disk limits/cleanup and runner registration are separate unfinished gates.

Bootstrap is an explicit exception to the future control-plane-only workflow:
Ansible uses the existing VM100 admin transport once to install the foundation.
Only prerequisite packages are installed; no Docker package replacement.
Official Moby rootless scripts are pinned to available tag v28.5.2 with SHA256
checksums; they launch the installed Ubuntu Docker 29.1.3 binary. The attempted
v29.1.3 upstream tag returned 404 during check mode, before host mutation.
Compatibility must pass the rootless daemon smoke check before proceeding.

## Verification

Check mode and syntax-check first. After apply verify rootless SecurityOptions,
separate DockerRootDir, no Swarm membership, no rootful socket permissions,
systemd resource limits, rootful service continuity and idempotent rerun.
Rollback stops the CI user's Docker unit and disables lingering; data/user remain
for inspection. Never prune the production daemon.

References: https://docs.docker.com/engine/security/rootless/ and
https://docs.gitlab.com/runner/executors/docker/ .

## Verified result

Applied by `ci-rootless-bootstrap.yml` using the existing SSH alias `vm100`.
The first installer invocation started the daemon but its CLI verification
failed because the upstream script expects `docker` beside itself. The playbook
now creates that symlink and independently enables/starts the user service.
Rerun completed with `ok=15 changed=0 failed=0`.

- User `homelab-ci`, UID 1001; no production Docker group or sudo grant.
- Rootless socket `/run/user/1001/docker.sock`.
- DockerRootDir `/home/homelab-ci/.local/share/docker`.
- SecurityOptions contains `rootless`; Swarm state is inactive.
- CI user access to `/var/run/docker.sock` fails with permission denied.
- User slice reports MemoryMax=4294967296, CPUQuotaPerSecUSec=2s, TasksMax=4096.
- Production daemon remains `/var/lib/docker`, Swarm active, 26 containers running.
- A disposable amd64 hello-world container pulled and exited successfully;
  observed manifest digest `sha256:11a3eb1597e864c51b3f56733cb2e8a90bf0c284bfc05f9444d81c558bc848aa`.
- Ansible lint passed. Check mode skips script downloads and dependent user-unit
  creation on a new host; it is not proof of install success. The live apply and
  idempotent rerun above provide that proof.

GitLab Runner itself is NOT yet installed or registered. CI pipeline execution,
registry publication, disk cleanup policy and Semaphore integration are pending.
No public documentation changes are required for this internal bootstrap.

Runner enrollment exposed a cgroup delegation gap: user@1001.service delegates
only memory/pids by default, so containers with CPU limits fail to start.
Delegate cpu/cpuset/io/memory/pids to this CI user manager only, restarting only
that user manager when the override changes. The outer 4 GiB/2 CPU slice cap
remains enforced by the host. Production Docker is not restarted.
