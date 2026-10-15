# KubeKosh LAN Lab

Status: installed on 2026-09-17.

## Goal

Provide a Kubernetes learning lab that is reachable only from the homelab LAN
or NetBird-routed clients. This lab is not part of the production Swarm
application set and must not add a VPS/public route.

## Placement

| Component | Placement | Notes |
|---|---|---|
| KubeKosh | VM100 standalone Docker Compose | Requires a privileged container because it runs K3s inside the container. |
| Persistence | `/opt/apps/kubekosh/data` on VM100 | Stores KubeKosh progress SQLite data mounted to `/data`. |
| Network | `homelab-net` only | Allows Pi5 Traefik to reach the container by Docker DNS without publishing VM100 ports. |
| DNS | Pi5 AdGuard | Existing wildcard rewrite `*.dungxbuif.com -> 10.10.0.5`; no lab-specific exact rewrite is required. |
| Ingress | Pi5 Traefik file provider | LAN-only router with `lan-only` middleware. No VPS HostSNI route is added. |

## Resource Plan

VM100 currently has 6 vCPU, 16 GiB RAM, about 129 GiB free disk, and no swap.
KubeKosh should be treated as a learning workload that can be stopped when not
in use. Initial limits are intentionally moderate:

```text
memory limit: 4 GiB
memory reservation: 1 GiB
cpu limit: 2 cores
```

If additional training platforms are added later, reassess VM100
RAM and add swap before running multiple lab stacks concurrently.

## Verification Plan

1. Confirm VM100 has no new host listener for KubeKosh.
2. Confirm the container is running and attached to `homelab-net`.
3. Confirm Pi5 Traefik can resolve and reach `kubekosh`.
4. Confirm AdGuard wildcard resolves `kubekosh.dungxbuif.com` to `10.10.0.5`.
5. Confirm LAN HTTPS returns the KubeKosh UI through Traefik.

## Deployment Evidence

KubeKosh was deployed from
`migration/kubekosh/docker-compose.yml` to `/opt/apps/kubekosh/docker-compose.yml`
on VM100. The container is attached to `homelab-net` with alias `kubekosh` and
publishes no VM100 host port.

Verification results:

```text
dig @10.10.0.5 kubekosh.dungxbuif.com +short -> 10.10.0.5 through wildcard DNS
https://kubekosh.dungxbuif.com/ via 10.10.0.5 -> HTTP 200
https://kubekosh.dungxbuif.com/ via VPS 103.82.21.202 -> HTTP 404
docker ps -> kubekosh Up, 80/tcp only
docker stats sample -> about 663 MiB of 4 GiB limit during bootstrap
```

Pi5 backups created during installation:

```text
/home/dungxbuif/edge/traefik/dynamic.yml.bak-kubekosh-20260917002345
/home/dungxbuif/edge/adguard/conf/AdGuardHome.yaml.bak-kubekosh-20260917002345
/home/dungxbuif/edge/adguard/conf/AdGuardHome.yaml.bak-remove-lab-exacts-20260917003441
```

## Rollback

On VM100:

```bash
cd /opt/apps/kubekosh
docker compose down
```

Then remove the Traefik router/service and AdGuard exact rewrite if the lab is
retired.
