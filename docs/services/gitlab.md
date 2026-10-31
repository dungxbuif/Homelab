# GitLab on VM100

## Current status (2026-10-31; route history retained below)

GitLab CE 18.11.11 is installed as one Docker Swarm service on VM100. The
container and internal web/SSH endpoints are healthy after the shared Redis
network recovery on 2026-10-16 and the follow-up overlay repair on
2026-10-31. **Public HTTPS now
returns 200 with a valid Let's Encrypt certificate, and Git-over-SSH on VPS
port 2222 reaches GitLab.** HTTPS temporarily terminates on VPS Traefik and
uses an isolated VM100 Rathole tunnel; direct Orange Pi GitLab HTTPS still
returns 404 because its file-provider router has not been applied. SSH to
Orange Pi resets before key exchange from both Mac and Pi5. The login page,
CSS, and basic route are verified; Git repository clone/push/pull, web
account login, and the local native backup/restore rehearsal are verified. The
off-host encrypted snapshot and scheduled recovery workflow are active; the
latest verified run is recorded in [Current backup status](#current-backup-status-2026-10-13).

GitLab's bundled Container Registry is now **trial-active**, not the lab's
production registry. The Pi5 `docker-registry` and
`registry.dungxbuif.com` remain in service. The trial domain and routing
limits are described below.

| Field | Value |
|---|---|
| Swarm service | `gitlab_gitlab` (stack `gitlab`) |
| Image | `gitlab/gitlab-ce:18.11.11-ce.0` |
| Placement | VM100 `vm100-prod`, `10.10.0.31` |
| Network | `gitlab-net`, `pg-net`, and `edge-http-net`; no published VM100 host ports |
| Internal web | `http://tasks.gitlab_gitlab:80` |
| Public HTTPS | `https://gitlab.dungxbuif.com/users/sign_in` 200; VPS Traefik Docker router `gitlab-temp@docker`, Let's Encrypt DNS-01 certificate; Orange Pi direct route 404 |
| Internal SSH | `tasks.gitlab_gitlab:22`; public `103.82.21.202:2222` |
| SSH tunnel | VPS `gitlab-ssh-rathole-server` (`7001` client control, `2222` public SSH) and VM100 Swarm `gitlab-ssh-tunnel_client` |
| Temporary HTTPS tunnel | VPS `gitlab-https-rathole-server` (`7002` client control, `8085` VPS Docker-network-only backend) and VM100 Swarm `gitlab-https-tunnel_client` |
| Database | Pi5 PostgreSQL 16.15, direct `postgres:5432`, dedicated `gitlabhq_production` database owned by `gitlab` |
| Redis | Pi5 shared `redis-prod:6379` on `gitlab-net`, GitLab DB `/2`, 1 GiB `noeviction`, AOF; see [Redis network operations](../runbooks/gitlab-redis-network.md) |
| VM100 data | `/opt/apps/gitlab/{config,logs,data}` |
| Resource envelope | 10 GiB/4 CPU limit, 2 GiB/1 CPU reservation; 256 MiB `/dev/shm` tmpfs |
| Secrets | Swarm `gitlab_db_password`, `gitlab_redis_password`, `gitlab_root_password`, `gitlab_ssh_tunnel_client`, and `gitlab_https_tunnel_client`; source files are mode 0600 under Pi5 `/ssd-data/infra/gitlab/secrets/` |
| Registration | Self-registration disabled (`signup_enabled=false`); `/users/sign_up` redirects to sign-in, admin-created users remain possible |
| Email | Disabled; password reset and notification email unavailable |
| S3 | Not enabled; RustFS is available on Pi5 if compatibility/bucket/key work is later approved |
| Trial Container Registry | `https://registry-gitlab.dungxbuif.com/v2/` 401 Bearer challenge, valid TLS via isolated VPS tunnel; filesystem storage on VM100; not a replacement for Pi5 registry yet |

## Operator workflow

1. Edit the secret-free [stack manifest](../../migration/gitlab-stack.yml)
   and [Omnibus config](../../migration/gitlab-omnibus.rb) in this repo.
   Validate with `docker stack config -c migration/gitlab-stack.yml` and
   `ruby -c migration/gitlab-omnibus.rb`.
2. Copy those files to Pi5 `/ssd-data/infra/gitlab/deploy/`. Deploy from
   that directory as Swarm manager with `docker stack deploy -c
   gitlab-stack.yml gitlab`. Never place passwords in either repo file.
3. Check `docker service ps gitlab_gitlab`, image health, internal login,
   Gitaly/Shell/Sidekiq with `gitlab-rake gitlab:check SANITIZE=true`,
   PostgreSQL connections, Redis DB2 memory, and VM100 disk/RAM.
4. For any stateful upgrade or manifest change, stop/scale GitLab to zero
   and wait for the old container to exit **before** starting a replacement
   against the same bind mounts. A prior overlapping rollout unlinked
   Gitaly's socket; restarting only Gitaly repaired it. Plan downtime and
   take VM100 config/data plus Pi5 DB backups first.
5. Once Orange Pi admin access is restored, apply the staged repository
   HTTPS file-provider route `gitlab.dungxbuif.com ->
   http://tasks.gitlab_gitlab:80` there and verify direct Orange Pi login
   200. Restore the VPS GitLab HostSNI term from its guarded backup **while
   the temporary HTTPS tunnel is still running**, then stop the temporary
   Docker-labeled HTTPS server and VM100 client. Verify public HTTPS has
   returned to Orange Pi, plus clone/push/pull over HTTPS and SSH, before
   deleting temporary credentials. Do not roll production edge tasks while
   new edge tasks remain stuck at `Accepted`.

## Temporary VPS HTTPS route

VPS Traefik has Docker provider enabled only for containers on VPS; this is
**not** an Orange Pi Swarm-label route. The new VPS
[Compose server](../../migration/gitlab-https-tunnel/docker-compose.yml)
joins only `gateway-network`. Its `traefik.*` container labels create
`Host(gitlab.dungxbuif.com)` on `websecure`, TLS via the existing
`letsencrypt` Cloudflare DNS-01 resolver, and backend port `8085` inside the
VPS Docker network. Only Rathole control `7002/tcp` is host-published. The
portless [VM100 client](../../migration/gitlab-https-tunnel/client-stack.yml)
forwards from that service to `tasks.gitlab_gitlab:80` on `gitlab-net`.
Token/Noise keys were generated outside the repo with the shared
[renderer](../../migration/gitlab-ssh-tunnel/render-runtime.py). VPS source
is `/root/gitlab-https-tunnel/runtime/server.toml` (mode 0600, image UID
1000); Pi5 client source is
`/ssd-data/infra/gitlab/secrets/https-tunnel-client.toml`, and an ignored
local copy is `credentials/gitlab-https-tunnel-client.toml`.

The VPS shared `/root/gateway/dynamic.yml` was changed **in place** with the
[guarded helper](../../migration/gitlab-https-tunnel/patch_gateway.py): only
the GitLab term was removed from `rathole-passthrough` HostSNI, leaving all
other rules intact and the bind-mount inode unchanged. Backup:
`/root/gateway/dynamic.yml.bak-gitlab-temp-20260915-171055-839423`.
The Docker router already served GitLab briefly before that removal; why
both matching router declarations selected the HTTP route in this runtime
was not established, so the explicit term removal avoids depending on it.
To roll back the shared file, use the helper's `--restore` with that backup
path; restore in place, not by renaming the bind-mounted file. Then stop
only `gitlab-https-tunnel_client` and the `gitlab-https-tunnel` VPS Compose
project after confirming the desired replacement route works. The VPS
certificate for GitLab currently has CN `gitlab.dungxbuif.com`, Let's
Encrypt issuer YR2, and expires 2026-12-14; ACME renewal remains to be
observed under this temporary topology.

## Container Registry trial

The bundled Registry is enabled in [Omnibus config](../../migration/gitlab-omnibus.rb)
with `registry_external_url 'https://registry-gitlab.dungxbuif.com'`, legacy
filesystem metadata (`registry['database']['enabled']=false`), and private
HTTP NGINX port `5005`. Its storage lives under the VM100 GitLab data bind
mount. GitLab's versioned Swarm config is
`gitlab_gitlab_omnibus_registry_trial_20260916`; the old config remains for
rollback. No GitLab host port was added.

The [trial VPS Compose server](../../migration/gitlab-registry-trial/docker-compose.yml)
publishes only authenticated Rathole control `7003/tcp`; its `8086/tcp`
backend is private on VPS Docker `gateway-network`. VPS Traefik Docker
labels terminate TLS for only the trial domain. The portless
[VM100 client](../../migration/gitlab-registry-trial/client-stack.yml) uses
Docker DNS `tasks.gitlab_gitlab:5005` on `gitlab-net` and Swarm secret
`gitlab_registry_trial_client`. Separate Noise credentials were generated
outside the repo and held at VPS
`/root/gitlab-registry-trial/runtime/{server,client}.toml`, Pi5
`/ssd-data/infra/gitlab/secrets/registry-trial-client.toml`, and ignored
local `credentials/gitlab-registry-trial-client.toml`. The external VPS
address in the client config is the same split-DNS exception as the other
tunnels; no app/DB internal IP was introduced.

Public `/v2/` returned 401 with a Bearer realm at
`https://gitlab.dungxbuif.com/jwt/auth`. Private project
`root/registry-trial` received ARM64 and AMD64 BusyBox tags; an OCI client
copied the ARM64 image back and matched its layer/config digests. The one-
time [trial report](../deployments/gitlab-registry-trial-2026-09-16.md)
records exact tags/digests, backup evidence, and rollback. For ongoing
deployments, use a project/group deploy token scoped `read_registry` for
pull and `read_registry` plus `write_registry` for push; root password was
used only inside a disposable smoke client and is not a deployment pattern.

**Pi5 registry remains production.** Public DNS reaches VPS, but lab split
DNS resolves the trial domain to Orange Pi and its direct Registry route
is not live. The smoke client used temporary host overrides only in its
own disposable container. Native Docker daemon and Swarm pull from lab
machines, CI, large uploads, multiarch manifest-list handling, garbage
collection, off-host scheduled backup, and restore have not been verified.
Do not retag production services or remove the Pi5 registry before an
internal DNS/edge route and native Docker pull test pass.

## Public SSH tunnel

The SSH path is separate from the existing Orange Pi HTTPS Rathole tunnel.
The VPS source is [server Compose](../../migration/gitlab-ssh-tunnel/docker-compose.yml)
and the VM100 source is [client stack](../../migration/gitlab-ssh-tunnel/client-stack.yml).
The VPS project is `/root/gitlab-ssh-tunnel`; its `runtime/server.toml` is
mode 0600 and owned by the image UID 1000. The matching client TOML is a
Swarm secret mounted read-only in `gitlab-ssh-tunnel_client`; its Pi5 source
is `/ssd-data/infra/gitlab/secrets/ssh-tunnel-client.toml`. A local ignored
copy lives under `credentials/gitlab-ssh-tunnel-client.toml`. The secret
contains a dedicated token and the server's Noise public key; the server's
Noise private key stays on the VPS. New runtime configs are generated with
[render-runtime.py](../../migration/gitlab-ssh-tunnel/render-runtime.py) and
are never committed. The external VPS address in the client config is a
deliberate exception to internal Docker DNS: split DNS would resolve the
gateway hostname to Orange Pi on the LAN.

The verified public SSH host key is ED25519 fingerprint
`SHA256:D7mj+Hm0JPxoDAuOm08h/fzj2tcCgPKYOY9u9DAUjc4`, matching the key inside
the GitLab container. Verify tunnel health with `docker service ps
gitlab-ssh-tunnel_client` on Pi5, `docker logs gitlab-ssh-rathole-server` on
VPS, and `ssh-keyscan -p 2222 -t ed25519 103.82.21.202`. A matching banner
and fingerprint prove routing, **not** account authorization or a completed
clone/push/pull test. The user's existing SSH alias for the GitLab domain
still targets the obsolete Pi5 `:2222` path; use the VPS address explicitly
until that alias is corrected after the full public cutover.

## Backup boundary

One-time GitLab backup after the Registry trial completed and included
`registry.tar.gz` with the trial project's manifests/layers:
`/opt/apps/gitlab/data/backups/1789494830_2026_09_15_18.11.11_gitlab_backup.tar`.
Separate before/after VM100 config snapshots and a prechange Pi5 DB dump
 were created (paths in the trial report). The current online GitLab backup
wrapper has been verified locally and restored into an isolated PostgreSQL 17
target after loading Pi5 globals; see [the rehearsal evidence](../deployments/backup-restore-rehearsal-2026-10-05.md).
The off-host encrypted snapshot and scheduled runner are active; restore
acceptance remains a separate pending drill. VM100 data
bind mounts include Gitaly repositories, uploads, and configuration; the
Pi5 PostgreSQL database is separate. A recoverable backup must include both
plus secret references and a restore drill. To restore public Git SSH,
also preserve the VPS mode-0600 `runtime/server.toml` and the Pi5 client
secret source; regenerate the pair together if either credential is lost.
The temporary HTTPS tunnel likewise needs its separate VPS runtime and Pi5
client secret source if it must be restored. S3 object storage, if enabled
later, does not replace a database/config/repository backup.

## Agent-readable facts

```yaml
service: gitlab_gitlab
status: public_https_vps_temporary_ssh_live
image: gitlab/gitlab-ce:18.11.11-ce.0
node: vm100-prod
network: gitlab-net, pg-net, edge-http-net
http_upstream: tasks.gitlab_gitlab:80
ssh_upstream: tasks.gitlab_gitlab:22
postgres_database: gitlabhq_production
postgres_endpoint: postgres:5432
redis_endpoint: redis-prod:6379/2
public_https_domain: gitlab.dungxbuif.com
public_https_current_status: 200
public_https_terminator: vps_gateway_traefik
public_https_router: gitlab-temp@docker
orange_pi_gitlab_route_current_status: 404
signup_enabled: false
public_ssh_endpoint: 103.82.21.202:2222
public_ssh_hostkey_ed25519: SHA256:D7mj+Hm0JPxoDAuOm08h/fzj2tcCgPKYOY9u9DAUjc4
ssh_tunnel_vps_container: gitlab-ssh-rathole-server
ssh_tunnel_vm100_service: gitlab-ssh-tunnel_client
ssh_tunnel_control_port: 7001
https_tunnel_vps_container: gitlab-https-rathole-server
https_tunnel_vm100_service: gitlab-https-tunnel_client
https_tunnel_control_port: 7002
https_tunnel_vps_private_backend_port: 8085
registry_trial_status: push_arm64_pull_arm64_push_amd64_backup_archive_verified
registry_trial_domain: registry-gitlab.dungxbuif.com
registry_trial_production_cutover: false
registry_trial_vm100_internal_endpoint: tasks.gitlab_gitlab:5005
registry_trial_vps_control_port: 7003
registry_trial_vps_private_backend_port: 8086
registry_trial_vps_container: gitlab-registry-trial-rathole-server
registry_trial_vm100_service: gitlab-registry-trial_client
registry_trial_storage: vm100_gitlab_bind_filesystem
registry_trial_metadata_database: false
pi5_registry_current_status: active
lab_native_docker_pull_verified: false
```
## Current backup status (2026-10-13)

GitLab is a separate backup class; it is not covered by the generic PostgreSQL
or CouchDB export. The VM100 `homelab-backup-gitlab.timer` is enabled and runs
the native Omnibus command `gitlab-backup create` beside the GitLab container,
then captures configuration/secrets and the local bundled Registry artifacts
before uploading and checking the encrypted Restic repository.

The latest verified run is `gitlab-20261012-193002` with snapshot ID
`0e4c88063586aece8b924c56422ee0272779bac7b5743cc517b7a858e18b0df3`. The run
completed successfully; the warning that `/var/opt/gitlab/backups` may be
readable by non-root users did not fail the job. Redis cache/session data is
deliberately excluded because it is rebuildable; Git repositories, uploads,
CI artifacts, Registry layers, config, and secrets remain in the GitLab-native
backup class. On 2026-10-13 the VM100 Mezon secret was corrected to match the
Pi5 executor secret after the GitLab notification was found to target an old
webhook; a warning-level delivery probe returned successfully.
