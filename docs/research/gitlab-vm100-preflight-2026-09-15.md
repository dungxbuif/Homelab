# GitLab VM100 Preflight - 2026-09-15

## Decision Boundary

This is a dated preflight and execution record, not the current status page.
GitLab was scheduled after VM100 routing/datastore cutovers and network review.
It is now healthy with public VPS HTTPS/SSH and a Registry trial; see the
[current runbook](../services/gitlab.md). Keep the app
and Gitaly repository storage on VM100; keep PostgreSQL
and shared `redis-prod` on Pi5. The operator chose shared Redis with a
queue-safe policy and public Git-over-SSH on 2026-09-15. Use Orange Pi
file-provider HTTPS routing without an HTTP host port on VM100; Git-over-SSH
needs a separate controlled TCP ingress, not an HTTP Traefik label.

## Measured Lab Preconditions

| Item | Current | Implication |
|---|---|---|
| VM100 disk | Proxmox `scsi0` 200 GiB; ext4 root 194 GiB usable, 58 GiB used, 137 GiB free after cache cleanup | Disk-size blocker resolved; monitor GitLab/Gitaly growth and thin-pool physical usage. |
| VM100 RAM | 15 GiB total, about 13 GiB available during this audit | GitLab's 16 GiB single-node baseline is close to the VM's total; tune for a small lab and remeasure after startup. |
| Pi5 PostgreSQL | 16.14 | Pin GitLab 18.x; GitLab 19.x requires PostgreSQL 17.x. Create a dedicated GitLab database/role with required extensions. |
| Pi5 Redis | 7.2.15 `redis-prod`, now 1 GiB `noeviction`; AOF and auth enabled; 4 GiB Pi5 swap active/unused | Operator chose sharing. Use GitLab Redis DB `/2` (OCR `/0`, MyPocket `/1`), monitor usage/error replies and Pi5 headroom. A separate instance remains fallback if contention appears. |
| Pi5 PgBouncer | Current `pool_mode = session` | Do not route GitLab through current `pgbouncer:6432`; initial GitLab uses private direct `postgres:5432`, also needed for migrations/backups. A later dedicated transaction-mode pooler is optional. |
| Pi5 RustFS | S3-compatible API already present | Optional for initial install. Test GitLab-compatible presigned URLs, multipart, streaming signatures, and ETag behavior before enabling consolidated object storage. |

## VM100 disk expansion work note (before execution)

The operator requested Codex to SSH and increase VM100 storage. Proxmox
`10.10.0.20` reports VM100 running, `scsi0` on NVMe-backed `local-lvm`
at 80G, no snapshot/lock, and about 269 GiB available in the thin pool.
Ubuntu VM100 uses ext4 root `/dev/sda1` on `/dev/sda`; `growpart` and
`resize2fs` are installed and sudo is non-interactive. Decision: online
expand only VM100 `scsi0` to **200G** (`qm resize 100 scsi0 200G`), then
grow guest partition 1 and ext4 filesystem in place. No new disk, VM
reboot, service redeploy, data deletion, or other VM change is planned.
Verification: compare Proxmox `qm config 100`/pool usage, guest `lsblk`/
`df -h /`, filesystem/partition type, representative Swarm task health,
and public Homepage/OCR/n8n routes after the operation. A disk increase
cannot be rolled back by shrinking the same volume; stop and inspect if
guest partition or filesystem growth fails instead of forcing a rewrite.

## Host allocation and unused-cache audit work note (before cleanup)

After online expansion, VM100 root is 194 GiB usable with 69 GiB used and
126 GiB available. Proxmox `local-lvm` NVMe thin pool is 348.8 GiB, about
80.9 GiB physically used and 268 GiB available. The registered thin volumes
are VM100 disk/cloud-init and Ubuntu template VM9000 base disk/cloud-init;
there are **no orphan VM volumes**. The template is a documented clone source
and is retained. `local` directory storage has one Ubuntu 22.04.5 installer
ISO (~2.0 GB), not referenced by any VM config; remove only that ISO and
verify it is absent afterwards. VM100 Docker has ~6.4 GB reclaimable build
cache; prune **build cache only**, not images, containers, or volumes, then
verify `docker system df`, root `df`, and production task/route health.
Retain old Compose images as the documented rollback path.

### Thin-pool discard follow-up (before configuration)

The guest cache cleanup lowered VM100 root usage, but Proxmox
`local-lvm` physical usage did not fall: VM100 `scsi0` currently lacks
`discard=on`, so guest trim/free notifications are not passed to the NVMe
thin pool. Proxmox's disk documentation requires Discard on the drive for
TRIM-enabled guests to return blocks. Decision: add only `discard=on` to
VM100 `scsi0`, preserving the same `local-lvm:vm-100-disk-0`, `replicate=0`,
and 200G size. Verify whether the running VM has an active or pending
config change; after the operator's planned restart, run `fstrim -v /`
and compare guest root and host thin-pool physical usage. Do not run
`fstrim` before the drive reports discard support in the guest.

## Execution and verification (2026-09-15)

- Proxmox `qm resize 100 scsi0 200G` changed only VM100 logical volume
  from 80.00 to 200.00 GiB. Ubuntu immediately saw `/dev/sda` 200G;
  `growpart /dev/sda 1` and online `resize2fs /dev/sda1` expanded root
  to 194 GiB usable without a VM restart. Before cleanup root was 69 GiB
  used / 126 GiB free; afterwards it was 58 GiB used / 137 GiB free.
- `pvesm list local-lvm` showed only VM100 disk/cloud-init and VM9000
  template base/cloud-init. `lvs` showed VM100 disk has no origin dependency
  on VM9000. The template was retained as a documented clone source;
  no orphan thin volume was deleted.
- `pvesm free` removed the unreferenced Ubuntu installer ISO. A fresh
  `pvesm list local` returned no volumes; `local` storage used fell from
  about 7.4 to 5.4 GiB.
- VM100 `docker builder prune -f` reported 11.53 GB reclaimed. Images and
  volumes were not pruned; `docker system df` then reported build cache
  13.56 GB with only 35.76 MB reclaimable. Old Compose rollback images
  remain. Public Homepage `/`, OCR `/healthz`, Family Tree `/login`,
  and n8n `/healthz` returned HTTP `200` after cleanup.
- Before restart, Proxmox `qm pending 100` showed `discard=on` pending and
  guest trim did not reclaim host thin-pool blocks. After the 2026-09-15
  restart, Discard became active. Guest `fstrim -v /` reported 136.1 GiB
  trimmed; Proxmox `local-lvm` physical usage fell from about 83.3 to
  66.0 GiB and available space rose from 265.6 to 282.9 GiB. The reclaim
  is now verified, not pending.

## Preparation Checklist For Operator

### Post-migration deployment decision (before GitLab install)

VM100 datastore clients are now Docker-DNS-clean, including MyPocket;
the network and resource audits are recorded separately. Pin GitLab CE
`gitlab/gitlab-ce:18.11.11-ce.0` (amd64 manifest verified), compatible
with Pi5 PostgreSQL 16.14 and Redis 7.2. Use one VM100-constrained
portless Swarm service on `homelab-net`. GitLab's own database and owner
role live in the shared Pi5 PostgreSQL **instance**, connected directly
as `postgres:5432` rather than session-mode PgBouncer. Create required
extensions in the dedicated database as superuser before GitLab migrations.

Use Swarm secrets for GitLab DB password, existing Redis password, and an
initial root password. A secret-free Omnibus config in this repo reads
those files from `/run/secrets`; GitLab config/log/data and Gitaly repos
remain VM100 bind mounts under `/opt/apps/gitlab`. External URL is
`https://gitlab.dungxbuif.com`, with TLS terminated by Orange Pi and
internal GitLab NGINX on HTTP port 80. Redis uses DB index 2. GitLab's
bundled PostgreSQL/Redis and optional Registry/Pages/KAS are disabled
for the initial small-lab install; no S3 object storage is needed yet.
Outgoing email is disabled until a working MTA/SMTP is provided, so signup
and password-recovery mail will not be available initially.

Docker `stack deploy` ignores the Compose `shm_size` key; the first task
started with only 64 MiB `/dev/shm`. Replace it with a 256 MiB `type: tmpfs`
mount at `/dev/shm` in the durable stack manifest, verify `docker stack
config` and the actual task mount/size after rollout. Do not keep an
unsupported key that only appears correct in YAML.

### Gitaly socket correction (before action)

The first `gitlab:check` found Shell/Redis/Sidekiq/migrations OK but Gitaly
FAIL because `/var/opt/gitlab/gitaly/gitaly.socket` was absent. Gitaly logs
showed it had bound that pathname; host `ss` still showed a listening UNIX
socket despite the pathname being absent. The tmpfs stack update overlapped
old/new GitLab task lifetimes on the **same** `/var/opt/gitlab` bind mount:
new Gitaly started around 15:56:28 UTC, while the old task did not finish
shutdown until 15:56:54 UTC. Old task cleanup may have unlinked the new
socket; this is a strong inference, not a confirmed Docker bug.

Restart only the Gitaly runit service in the remaining healthy GitLab task,
verify its socket exists, rerun the Gitaly check, and confirm login/SSH
remain available. Do not roll the whole GitLab container or modify its DB.
For future stateful GitLab upgrades, avoid an automatic overlapping bind-
mount rollout: explicitly stop/scale to zero and wait for old container
exit before starting the replacement, accepting planned downtime. Keep a
VM100 data/config backup and database snapshot before such upgrades.

Route HTTPS through Orange Pi file provider and VPS HostSNI after internal
health. Git-over-SSH requires a separate Rathole TCP ingress (tentative
public port 2222, not VPS admin SSH) to `gitlab:22` on the edge overlay,
and `gitlab_rails['gitlab_shell_ssh_port']=2222`. Confirm that port is free
at VPS and that Orange Pi/VPS administrative SSH is usable **before**
publishing or claiming SSH availability. Current Orange Pi SSH handshake
resets/times out and VPS root authentication rejects available keys;
neither public routing edit can be safely applied through that state.
Internal service deployment can proceed, but external reachability remains
unverified until access is restored. Verification: DB/Redis DNS/auth,
GitLab task convergence and health, internal HTTP, process resource sample,
then public HTTPS plus clone/push/pull and SSH handshake only after ingress
is configured. Roll back only GitLab service/config, never existing Pi5
datastore data or unrelated routes.

1. Done 2026-09-15: expanded VM100 SSD-backed disk from 80 to 200 GiB;
   root has 137 GiB free after unused build cache cleanup. Reserve growth
   for GitLab repositories and monitor thin-pool usage.
2. Done 2026-09-15: created an isolated GitLab PostgreSQL database and role
   database `gitlabhq_production`, role `gitlab`), verify UTF-8 and extensions
   required by the pinned 18.x release (`amcheck`, `btree_gist`, `pg_trgm`,
   `plpgsql`). Keep credentials out of git; the role must be usable from the
   private GitLab-to-Postgres network.
3. Done 2026-09-15: shared Redis 7.2 `redis-prod` retained auth/AOF/data;
   raised `maxmemory` to 1 GiB and changed policy to `noeviction` before
   GitLab. Monitor all clients because this changes the shared instance;
   do not clear data or close its existing LAN/overlay endpoints.
4. Reserve `gitlab.dungxbuif.com` for HTTPS UI and Git-over-HTTPS; add it to
   Orange Pi file routing and VPS HostSNI allow-list at deployment. The
   operator also requested public Git-over-SSH; design one controlled
   Rathole/VPS TCP ingress on a non-conflicting port, separate from VPS SSH.
5. Optional: provide GitLab-specific RustFS S3 key/buckets for artifacts,
   uploads, LFS, packages, and backups. GitLab repositories/Gitaly stay on
   VM100 local SSD; consolidated object storage does not cover backups or the
   optional container registry. Enable S3 only after compatibility tests.

## Deployment And Verification Plan

- Select an exact patched GitLab 18.x Docker image compatible with Pi5 PG16;
  pin it, do not deploy a floating `latest` tag. Start as a VM100-constrained
  one-replica Swarm service with persistent config/log/data/Gitaly mounts,
  adequate shared memory, and no HTTP host port.
- Disable bundled PostgreSQL and Redis and configure direct private DNS
  `postgres:5432` plus shared `redis-prod:6379`. Keep secret-bearing
  Omnibus config mode 0600 and out of the repo. GitLab package configuration,
  DB setup/extension readiness, and backup/restore path need fresh validation.
- Expose HTTPS through Orange Pi `tasks.gitlab:<HTTP port>` file route and VPS
  allow-list only after internal health/readiness and a repository create,
  clone, push, and pull smoke test. Verify backup of GitLab DB/config/repos;
  do not assume RustFS object storage is a complete backup.
- Audit memory, disk, Pg connections, Redis persistence, Gitaly I/O, and
  public ingress after startup. Keep a rollback image/config snapshot.

## Executed internal deployment and remaining public work

The role `gitlab` owns `gitlabhq_production`; `amcheck`, `btree_gist`,
`pg_trgm`, and `plpgsql` are installed. Three GitLab Swarm secrets were
created without repo plaintext. Disposable VM100 Swarm tasks authenticated
to direct `postgres:5432` (`SELECT 1`) and `redis-prod:6379/2` (`PONG`)
and were removed. The pinned CE image was pulled on VM100 and the stack
deployed as `gitlab_gitlab`; internal task health is healthy with zero
restarts, no OOM, 256 MiB `/dev/shm`, and no published host ports.
Internal login returned 200 and SSH banner was reachable via Docker DNS.
The first `gitlab:check` found Gitaly socket missing after overlapping
task replacement; restarting only Gitaly restored it. The second check
reported GitLab Shell, Gitaly, Redis, Sidekiq, migrations, and config OK.
Pi5 PostgreSQL held 60/100 total connections after startup (37 GitLab),
and Redis DB2 had 631 keys under 2.54 MiB logical memory. Pi5 swap used
134 MiB but no `si/so` churn appeared in five samples.

On 2026-09-15, the configured `gateway` SSH alias reached the VPS. Its live
Traefik HostSNI allow-list already includes `gitlab.dungxbuif.com`, and VPS
port 2222 is unused. Orange Pi `10.10.0.2:22` accepts TCP but resets before
SSH key exchange from both Mac and Pi5; the edge Traefik task and existing
web routes continue running. Before any ingress change, attempt one short-
lived, read-only regular Swarm service pinned to the edge with the live
dynamic file bind-mounted read-only; compare only its SHA-256 and route
names with the repo source. Remove it whether it runs or stalls. Do not
replace the production edge task or dynamic file while the worker cannot
start a disposable service and the live file cannot be reconciled.

At this preflight stage, remaining work was Orange Pi ingress or a verified
temporary path, public HTTPS, and clone/push/pull. The later temporary VPS
route is documented below. No scheduled/off-host GitLab backup, SMTP, or
RustFS object-storage integration was verified at this stage.

### Git-over-SSH route decision

Because the Orange Pi cannot start an audit task or complete SSH key exchange,
do not roll its production Rathole or Traefik tasks to add Git SSH. Instead,
deploy an isolated Rathole server Compose project on the VPS, independent of
`/root/gateway` and its existing `7000`/HTTP tunnel. Bind `7001/tcp` for the
outbound VM100 client and `2222/tcp` for public Git SSH. The client is a
portless Swarm service pinned to VM100 on `homelab-net` and forwards only to
`tasks.gitlab_gitlab:22` by Docker DNS; the VPS server never joins that
overlay. Pin both sides to the existing VPS Rathole image digest. Use a new
per-service random token and a Noise NK server keypair: server private key
and token stay in a mode-0600 VPS runtime config, client public key and token
in a Swarm secret. Keep both values out of repo files, task logs, and final
responses. The external VPS static address is the only literal IP exception
in the client config because split DNS sends the public gateway hostname to
the Orange Pi on the LAN.

Verified `2222`/`7001` were unbound, rendered and parsed both TOML files,
started only the new VPS project, then the client service. The VPS image
runs as UID 1000, so its mode-0600 server config is owned by UID/GID 1000;
the renderer now sets this ownership. The VPS server established a Noise
control channel for `gitlab_ssh`, and `gitlab-ssh-tunnel_client` converged on
VM100. Public `103.82.21.202:2222` returned the GitLab SSH banner; its
ED25519 fingerprint matched the key inside the GitLab container exactly.
The existing gateway Compose project was not restarted. Clone/push/pull
using a temporary GitLab project remains untested until HTTPS ingress and
account/key setup work. If future client convergence fails, remove only
the new client and VPS project; preserve the existing gateway stack. The
public web domain remained incomplete at this SSH-only stage. The temporary
VPS HTTPS deployment below supersedes this stage's status.

### Temporary VPS HTTPS cutover and registration (2026-09-16)

Orange Pi admin SSH still resets before key exchange and its direct GitLab
file route remains staged (direct Orange Pi GitLab login returns 404). The
operator approved an isolated HTTPS tunnel instead: a portless VM100 Swarm
client forwards Docker DNS `tasks.gitlab_gitlab:80` to a VPS Rathole server
on authenticated `7002/tcp`; its HTTP backend `8085/tcp` is only on VPS
Docker `gateway-network`. VPS Traefik Docker labels serve
`gitlab.dungxbuif.com` using a valid Let's Encrypt certificate. A guarded,
parser-checked, in-place edit removed only GitLab's HostSNI term from the
VPS shared TCP passthrough rule; the backup and rollback are in
[GitLab service runbook](../services/gitlab.md). The existing SSH tunnel,
other public domains, and GitLab data were left intact.

Public `/users/sign_in` and its CSS returned 200 with certificate
verification; `:2222` still matched GitLab's internal ED25519 key. GitLab
`signup_enabled` was `true` after public cutover, so the operator approved
setting it to `false` through Rails. The public `/users/sign_up` now
redirects to `/users/sign_in`. Actual account authentication, project
creation, clone/push/pull, CI, scheduled/off-host backup and restore, SMTP,
and RustFS/S3 integration remain unverified. These are separate from the
verified public login-page availability.

## Primary References

- [GitLab installation requirements](https://docs.gitlab.com/install/requirements/)
- [GitLab Docker installation](https://docs.gitlab.com/install/docker/installation/)
- [GitLab external database configuration](https://docs.gitlab.com/omnibus/settings/database/)
- [GitLab Redis configuration](https://docs.gitlab.com/omnibus/settings/redis/)
- [GitLab PgBouncer behavior](https://docs.gitlab.com/administration/postgresql/pgbouncer/)
- [GitLab object storage compatibility](https://docs.gitlab.com/administration/object_storage/)
- [GitLab Gitaly disk guidance](https://docs.gitlab.com/administration/gitaly/)
