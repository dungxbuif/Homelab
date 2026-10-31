---
type: Service
title: GitLab on VM100
description: GitLab CE runtime, temporary VPS routes, registry trial, backup boundary and rollback
generated:
  by: claude-code/opus-5.5
  at: "2026-10-31T00:00:00+07:00"
stale_after: "2027-01-29T00:00:00+07:00"
---

# GitLab on VM100

## Source

| Field | Value |
|---|---|
| Upstream | https://gitlab.com/gitlab-org/gitlab (Omnibus image `gitlab/gitlab-ce`) |
| Pinned version | `gitlab/gitlab-ce:18.11.11-ce.0` (`sha256:10528ba5…`) |
| Deploy source | Swarm stack `gitlab`; stack file location in `homelab-ops` (unverified) |
| Repo docs | none (third-party) |

## Current status (2026-10-31)

GitLab CE 18.11.11 runs as one Swarm service on VM100 and is healthy after the
[Redis network repair](../deployments/gitlab-redis-network-repair-2026-10-31.md).
Public HTTPS (VPS route check `302` on 2026-10-31) and Git-over-SSH on VPS
`:2222` both go through **temporary VPS Rathole tunnels** that bypass the Pi5
edge. The Pi5 Traefik has no working GitLab route (direct request 404). The
upgrade is on hold (see below). The bundled Container Registry is a trial; the
Pi5 `docker-registry` remains production.

| Field | Value |
|---|---|
| Swarm service | `gitlab_gitlab` (stack `gitlab`) |
| Image | `gitlab/gitlab-ce:18.11.11-ce.0` (`sha256:10528ba5…`) |
| Placement | VM100 `vm100-prod`, `10.10.0.31` |
| Networks | `gitlab-net`, `pg-net`, `edge-http-net`; no VM100 host ports |
| Internal endpoints | web `tasks.gitlab_gitlab:80`, SSH `:22`, registry `:5005` |
| Public HTTPS | `https://gitlab.dungxbuif.com`, TLS on VPS Traefik Docker router `gitlab-temp@docker` (Let's Encrypt DNS-01; cert expires 2026-12-14, renewal not yet observed) |
| Public SSH | `103.82.21.202:2222`, ED25519 `SHA256:D7mj+Hm0JPxoDAuOm08h/fzj2tcCgPKYOY9u9DAUjc4` |
| Database | Pi5 PostgreSQL 16.15, direct `postgres:5432`, DB `gitlabhq_production`, owner `gitlab` |
| Redis | Pi5 `redis-prod:6379/2` over `gitlab-net`; see [Redis runbook](../runbooks/gitlab-redis-network.md) |
| VM100 data | `/opt/apps/gitlab/{config,logs,data}` (repos, uploads, registry layers) |
| Resources | limit 10 GiB / 4 CPU, reservation 2 GiB / 1 CPU, `/dev/shm` 256 MiB |
| Swarm secrets | `gitlab_db_password`, `gitlab_redis_password`, `gitlab_root_password`, `gitlab_ssh_tunnel_client`, `gitlab_https_tunnel_client`, `gitlab_registry_trial_client`; sources mode 0600 in Pi5 `/ssd-data/infra/gitlab/secrets/` |
| Sign-up / email / S3 | disabled / disabled (no password-reset mail) / not enabled |

## Tunnels (VPS ↔ VM100)

| Purpose | VPS container (control port) | VPS backend | VM100 Swarm client | Target |
|---|---|---|---|---|
| SSH | `gitlab-ssh-rathole-server` (`7001`) | public `2222` | `gitlab-ssh-tunnel_client` | `tasks.gitlab_gitlab:22` |
| HTTPS (temporary) | `gitlab-https-rathole-server` (`7002`) | `8085`, VPS Docker network only | `gitlab-https-tunnel_client` | `tasks.gitlab_gitlab:80` |
| Registry trial | `gitlab-registry-trial-rathole-server` (`7003`) | `8086`, VPS Docker network only | `gitlab-registry-trial_client` | `tasks.gitlab_gitlab:5005` |

Sources in `homelab-ops/migration/`: `gitlab-ssh-tunnel/`,
`gitlab-https-tunnel/`, `gitlab-registry-trial/` (server Compose, client stack;
runtime configs rendered by `gitlab-ssh-tunnel/render-runtime.py`, never
committed). VPS runtime TOMLs (mode 0600, UID 1000) live in
`/root/gitlab-ssh-tunnel/runtime/`, `/root/gitlab-https-tunnel/runtime/`,
`/root/gitlab-registry-trial/runtime/`; Pi5 client sources in
`/ssd-data/infra/gitlab/secrets/{ssh,https}-tunnel-client.toml` and
`registry-trial-client.toml`. Client configs use the VPS IP directly on
purpose. Regenerate a server/client pair together if either is lost.

For the HTTPS route, the VPS shared `/root/gateway/dynamic.yml` had only the
GitLab term removed from the `rathole-passthrough` HostSNI rule (via
`homelab-ops/migration/gitlab-https-tunnel/patch_gateway.py`). Backup:
`/root/gateway/dynamic.yml.bak-gitlab-temp-20260915-171055-839423`. Roll back
with the helper's `--restore` (in place — the file is bind-mounted; never
rename it).

**Moving HTTPS back to the lab edge** (target: Pi5 Traefik, the Orange Pi is
gone): add `gitlab.dungxbuif.com → http://tasks.gitlab_gitlab:80` to
`homelab-ops/migration/traefik/dynamic.yml`, verify direct Pi5 login 200,
restore the VPS HostSNI term while the temporary tunnel still runs, then stop
`gitlab-https-tunnel_client` and the VPS `gitlab-https-tunnel` project and
re-test HTTPS/SSH clone/push/pull. Update the user's SSH alias for the GitLab
domain, which still points at an obsolete `:2222` path.

## Container Registry trial

`registry_external_url 'https://registry-gitlab.dungxbuif.com'`, filesystem
storage on VM100, metadata DB off, internal NGINX `:5005`; Swarm config
`gitlab_gitlab_omnibus_registry_trial_20260916` (previous config kept for
rollback). `/v2/` answers 401 with Bearer realm
`https://gitlab.dungxbuif.com/jwt/auth`. ARM64/AMD64 push and ARM64 pull were
verified from a disposable client with host overrides. Native lab Docker/Swarm
pull, CI use, GC and restore are **not** verified, and lab split DNS has no
route for the trial domain. Use deploy tokens (`read_registry` to pull,
`+write_registry` to push), never the root password. Do not retag production
images away from `registry.dungxbuif.com`.

## Operator workflow

1. Edit `homelab-ops/migration/gitlab-stack.yml` and `gitlab-omnibus.rb`
   (secret-free). Validate: `docker stack config -c migration/gitlab-stack.yml`,
   `ruby -c migration/gitlab-omnibus.rb`.
2. Reconcile first: the deployed copy in Pi5 `/ssd-data/infra/gitlab/deploy/`
   has drifted from the repo source.
3. Copy to `/ssd-data/infra/gitlab/deploy/` and deploy from Pi5:
   `docker stack deploy -c gitlab-stack.yml gitlab`.
4. Stateful changes: scale to 0 and wait for the old container to exit before
   a new task starts on the same bind mounts (an overlap once unlinked Gitaly's
   socket; restarting Gitaly fixed it).
5. Verify: `docker service ps gitlab_gitlab`, `gitlab-rake gitlab:check
   SANITIZE=true`, `/-/health` and `/-/readiness` 200, a valid-token
   `/api/v4/user`, VM100 disk/RAM.
6. Tunnel health: `docker service ps gitlab-ssh-tunnel_client` (Pi5),
   `docker logs gitlab-ssh-rathole-server` (VPS),
   `ssh-keyscan -p 2222 -t ed25519 103.82.21.202` (fingerprint above).

## Upgrade hold

Next patch is `18.11.14`; major path `18.11.14 → 19.2.10 → 19.5.3`. Blocked
until: PostgreSQL 17 is available for GitLab, the deploy-source drift is
reconciled, and a native backup plus isolated restore is feasible.

## Backup boundary

**No scheduled GitLab backup exists.** The restic `gitlab` class has no timer,
and the native backup (~14 GB including ~2 GB `registry.tar.gz`) was stopped
before completion on 2026-10-31. Databasus backs up `gitlabhq_production`
without restore verification. A recoverable backup needs: native
`gitlab-backup create` archive (repos, uploads, artifacts, registry), the
config/secrets (`gitlab-secrets.json`, `gitlab.rb`), the Pi5 database plus
PostgreSQL globals, the exact version/edition, and the tunnel credentials
above. Redis DB 2 is rebuildable and excluded. A VM snapshot alone is not
enough.

## Agent-readable facts

```yaml
service: gitlab_gitlab
status: healthy_public_via_vps_temporary_tunnels
image: gitlab/gitlab-ce:18.11.11-ce.0
node: vm100-prod
networks: [gitlab-net, pg-net, edge-http-net]
http_upstream: tasks.gitlab_gitlab:80
ssh_upstream: tasks.gitlab_gitlab:22
postgres: postgres:5432/gitlabhq_production
redis: redis-prod:6379/2
public_https_terminator: vps_gateway_traefik (gitlab-temp@docker)
pi5_edge_gitlab_route: absent (404)
public_ssh_endpoint: 103.82.21.202:2222
signup_enabled: false
registry_trial_domain: registry-gitlab.dungxbuif.com
registry_trial_production_cutover: false
pi5_registry_current_status: active
scheduled_backup: none
upgrade_status: on_hold
```

## Gate status

| Gate | State | Evidence / exception (expiry) |
|---|---|---|
| G0 Intake | fail | no `app.yml` |
| G1 Build | partial | upstream image pinned by digest; no scan |
| G2 Security | partial | Swarm secrets used, sign-up disabled; temporary VPS tunnels bypass the Pi5 edge |
| G3 Runtime | partial | in stack `gitlab`; routes are temporary tunnels |
| G4 Data | fail | no scheduled backup; Databasus DB job without restore verification; repos/registry on VM100 not backed up |
| G5 Observability | not assessed | |
| G6 Release | not assessed | upgrade on hold |
| G7 Docs | partial | this doc |
| G8 Operate | not assessed | |
