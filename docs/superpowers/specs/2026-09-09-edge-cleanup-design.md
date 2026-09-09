# Edge Cleanup Design

**Goal:** Make the Orange Pi Traefik deployment the single documented and deployable home-edge configuration, then remove obsolete Caddy and Nginx artifacts without touching PostgreSQL.

## Canonical Runtime

- Orange Pi Zero 3 (`10.10.0.2`) remains the Swarm worker and home edge.
- `edge_traefik`, `edge_rathole`, and `edge_adguardhome` remain active.
- `edge_caddy` is retired and removed after route and ingress verification.
- The VPS continues to run `gateway-traefik` and `rathole-server`.
- Pi5 remains the Swarm manager and datastore host; it does not run an edge proxy.

## Route Scope

- Preserve the routes already present in `/opt/edge/traefik/dynamic.yml`.
- Treat `n8n.dungxbuif.com`, `gitlab.dungxbuif.com`, and `git.dungxbuif.com` as retired. Remove their stale references from current documentation, scripts, and rollback configuration.
- Leave PostgreSQL unchanged. Do not add, remove, expose, restart, or reconfigure PostgreSQL or a PostgreSQL edge route.
- Keep `grafana.dungxbuif.com` retired unless a separate request restores it.

## Source Of Truth

- Replace the Caddy-based `migration/edge-stack.yml` with a Traefik-based Swarm stack matching the live services.
- Add repository copies of the active Traefik static and dynamic configuration without secrets or ACME account data.
- Update current architecture documentation to say Orange Pi Traefik, Rathole, and AdGuard.
- Update the edge publishing helper to manage the Orange Pi Traefik dynamic configuration and the VPS Traefik SNI allow-list.
- Historical migration documents remain available but are clearly marked superseded where they could otherwise be executed as current instructions.

## Cleanup And Rollback

- Create one timestamped rollback archive before deleting runtime artifacts.
- The archive contains the live Swarm service specifications and the Orange Pi Caddy, Traefik, Rathole, and AdGuard configuration trees. Secret-bearing files retain restrictive permissions and are not committed.
- Remove the disabled `edge_caddy` service after verification.
- Remove obsolete Caddy images, old Caddy assets, redundant configuration backups, and stopped Swarm task containers on Orange Pi.
- Remove obsolete Pi5 edge images, directories, and the old edge compose backup after the rollback archive is confirmed.
- Remove legacy VPS Nginx configuration and backups after confirming `gateway-traefik` owns public ingress.
- Keep `/opt/edge/traefik/test-letsencrypt/acme.json` in place because it is the active production ACME store, despite the misleading directory name.

## Verification

- Validate the repository stack and Traefik configuration before deployment.
- Verify Orange Pi remains `Ready` and all three retained edge services are `1/1`.
- Verify split-horizon DNS resolves active `*.dungxbuif.com` names to `10.10.0.2`.
- Smoke-test every retained Traefik hostname over LAN and through the VPS Rathole path.
- Confirm retired `n8n`, `gitlab`, `git`, and `grafana` hosts do not have active home-edge routers.
- Confirm PostgreSQL containers, ports, and service configuration are unchanged.
- Confirm the repository has no active documentation or automation pointing to Pi5 Caddy, Orange Pi Caddy, or VPS Nginx.
