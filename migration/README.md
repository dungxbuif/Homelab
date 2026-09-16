# migration/ - Orange Pi edge assets

This directory contains deployable source for the Orange Pi edge (Traefik,
Rathole, AdGuard Home), Pi5 resource assets, and the GitLab VM100 stack. The edge Swarm
stack is scheduled with the `edge=true` node label and uses the external
`homelab-net` overlay.

| File | Purpose | Status |
|---|---|---|
| `edge-stack.yml` | Canonical Swarm stack for Traefik, Rathole, and AdGuard Home; Traefik routes use the file provider only | Current |
| `traefik/traefik.yml` | Traefik static configuration | Current |
| `traefik/dynamic.yml` | Approved HTTP routers, middleware, and upstream services; GitLab HTTPS stanza is source-only until Orange Pi access returns | Current routes plus staged GitLab |
| `redis-prod-overlay.override.yml` | Secret-free Pi5 Compose override deployed as `/ssd-data/infra/redis-prod/docker-compose.override.yml`; keeps Redis default bridge and adds `homelab-net` DNS alias `redis-prod` | Current |
| `pi5-swap.service` | Pi5 systemd unit deployed as `/etc/systemd/system/homelab-pi5-swap.service` for the 4 GiB NVMe swapfile | Current |
| `pi5-swap-sysctl.conf` | Pi5 drop-in deployed as `/etc/sysctl.d/90-homelab-pi5-swap.conf`; `vm.swappiness=10` | Current |
| `gitlab-stack.yml` | GitLab CE 18.11.11 Swarm stack; VM100 placement, portless HTTP/SSH/Registry, bind data, secrets, versioned Omnibus config, 256 MiB `/dev/shm` tmpfs | Deployed; public HTTPS temporary VPS path, Orange Pi route pending |
| `gitlab-omnibus.rb` | Secret-free GitLab config referencing Swarm `/run/secrets`; direct Pi5 PostgreSQL, shared Redis DB2, bundled filesystem Registry trial on private NGINX `:5005` | Deployed trial config |
| `gitlab-ssh-tunnel/docker-compose.yml` | Isolated VPS Rathole server on `7001`/`2222`; separate from current HTTPS tunnel | Deployed |
| `gitlab-ssh-tunnel/client-stack.yml` | Portless Rathole client on VM100 to GitLab SSH over Docker DNS | Deployed |
| `gitlab-ssh-tunnel/{server,client}.toml.template` | Secret-free Noise/token runtime templates | Current |
| `gitlab-ssh-tunnel/render-runtime.py` | Generates matching private runtime configs on VPS; never prints token or keys | Current |
| `gitlab-https-tunnel/docker-compose.yml` | VPS-local Docker-labeled GitLab HTTPS Rathole server; publishes only control `7002`, private backend `8085` on `gateway-network` | Temporary deployed |
| `gitlab-https-tunnel/client-stack.yml` | Portless VM100 Rathole client to GitLab HTTP over Docker DNS | Temporary deployed |
| `gitlab-https-tunnel/{server,client}.toml.template` | Secret-free Noise/token runtime templates; rendered with shared SSH-tunnel renderer | Current |
| `gitlab-https-tunnel/patch_gateway.py` | Parser-checked one-term VPS HostSNI patch/restore that preserves Traefik's bind-mount inode | Executed; backup on VPS |
| `gitlab-registry-trial/docker-compose.yml` | VPS-local Docker-labeled trial Registry Rathole server; only control `7003` published, private `8086` backend on `gateway-network` | Trial deployed |
| `gitlab-registry-trial/client-stack.yml` | Portless VM100 client to GitLab Registry NGINX `tasks.gitlab_gitlab:5005` over Docker DNS | Trial deployed |
| `gitlab-registry-trial/{server,client}.toml.template` | Secret-free Noise/token templates; rendered with shared SSH-tunnel renderer | Current |

The active certificate store remains at
`/opt/edge/traefik/test-letsencrypt/acme.json`. Its directory name is retained
for production compatibility. Certificate state and DNS provider secrets are
runtime-only and must never be added to this repository.

## Deployment

Export `CF_DNS_API_TOKEN` in the operator environment, then deploy the stack
from the repository root:

```sh
docker stack deploy -c migration/edge-stack.yml edge
```

The deployable files intentionally contain no token value or certificate
account data. Traefik reads the provider token from the deployment environment.

## Swarm service routing

Orange Pi Traefik uses the file provider for every route. Swarm workloads stay
portless on `homelab-net`; `traefik/dynamic.yml` targets them through Swarm DNS
as `tasks.<service>:<container-port>`. Homepage now routes both
`dungxbuif.com` and `www.dungxbuif.com` to `tasks.homepage:80` on VM100; n8n,
OpenClaw, MyPocket, NetBird, and RelayHub use the same routing model. The
Compose Homepage container and its former `10.10.0.31:18081` route are kept
only as a stopped rollback path.

`mezonhook.dungxbuif.com` now targets `tasks.mezonhook:8080` on VM100.
Its former Compose container and `10.10.0.31:18084` route are retained only
as a stopped rollback path.

`family.dungxbuif.com` now targets `tasks.family-tree:3000` on VM100. Its
source/uploads are VM100 bind mounts; the old Compose container and
`10.10.0.31:18085` route remain only as a stopped rollback path.

`ocr.dungxbuif.com` now targets `tasks.macocr-proxy:8080` on VM100. The
proxy still calls the native Mac OCR engine on `10.10.0.6:8787`; the old
Compose container and `10.10.0.31:18080` route remain only as a stopped
rollback path. Do not attach a fresh diagnostic container to `homelab-net`
on Orange Pi during cutovers; probe from the existing Traefik task network
namespace to avoid the observed edge overlay disruption.

Do not enable the Traefik Swarm provider through a remote Docker socket proxy.
The edge worker intermittently lost the overlay path to the manager-side proxy,
which made otherwise healthy routes return `502`.

## Active routes

The live Orange Pi dynamic configuration publishes these approved hostnames.
The repository source now also contains a **staged, not-yet-deployed**
`gitlab.dungxbuif.com` router to `tasks.gitlab_gitlab:80`. Public Git SSH
on VPS `:2222` is live. **Public GitLab HTTPS is temporarily live on VPS**
through a Docker-labeled VPS-local Rathole backend and a portless VM100
client; the GitLab term was removed from VPS TCP passthrough, with an in-
place backup. Orange Pi administrative SSH still resets before key exchange,
and its direct GitLab HTTPS router is not live (`404`). Do not treat the
Orange Pi source router as deployed. See [GitLab runbook](../docs/services/gitlab.md).
The bundled GitLab Registry trial on `registry-gitlab.dungxbuif.com` is a
separate VPS-labeled HTTP tunnel, not an Orange Pi file route. Pi5
`docker-registry` remains production; do not replace its domain or service
until native lab Docker/Swarm pull works without disposable host overrides.
See [trial evidence](../docs/deployments/gitlab-registry-trial-2026-09-16.md).

- `dungxbuif.com`
- `www.dungxbuif.com`
- `cdn.dungxbuif.com`
- `storage.dungxbuif.com`
- `registry.dungxbuif.com`
- `speed.dungxbuif.com`
- `pgadmin.dungxbuif.com`
- `couchdb.dungxbuif.com`
- `sync-db.dungxbuif.com`
- `llm.dungxbuif.com`
- `ocr.dungxbuif.com`
- `money.dungxbuif.com`
- `mezonhook.dungxbuif.com`
- `family.dungxbuif.com`
- `openclaw.dungxbuif.com`
- `n8n.dungxbuif.com`
- `relayhub.dungxbuif.com`

The earlier Caddy deployment is retired. Its repository examples were archived
under `docs/archived/edge-caddy-era/` and are not current deployment
instructions. GoClaw routing is intentionally absent pending a separate plan;
OpenClaw is a separate VM100 service and is not the removed GoClaw backend.
`transfer.dungxbuif.com` was retired when PairDrop/Coturn were removed from the
VPS on 2026-09-13. The live Orange Pi Traefik route was removed from
`/opt/edge/traefik/dynamic.yml`; because LAN DNS still sends the wildcard domain
to the edge, the expected response for this retired hostname is Traefik `404`.
