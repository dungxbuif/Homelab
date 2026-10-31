# Portainer CE and VM100 Swarm manager — 2026-10-31

## Intended behavior

Install Portainer CE as a LAN-only Docker Swarm control UI and promote
`vm100-prod` to a Swarm manager. Portainer must not publish host ports or gain
a public Internet route. The Pi5 (`rpivn`) remains the Portainer Server's
placement node so its local `portainer_data` volume remains authoritative;
Portainer Agent runs globally to observe all Linux Swarm nodes.

## Technical decision

- Use the official Portainer CE Swarm pattern: one Server service and a global
  Agent service on the Swarm overlay.
- Keep the Server constrained to the Pi5 manager and expose its HTTP listener
  only through the existing LAN-only Pi5 Traefik route
  `portainer.dungxbuif.com`.
- Promote `vm100-prod` to a second manager and allow the Agent to report VM100
  directly. This improves manager access, but two managers still require both
  nodes for quorum; it is not three-manager failure-tolerant HA.
- Keep Semaphore, `homelab-provisioner`, and Git/IaC as deployment authority;
  Portainer is an operational UI, not a second production source of truth.

## Affected flow and verification

- New stack source: `homelab-ops/swarm/portainer/stack.yml`.
- New LAN route: `portainer.dungxbuif.com` -> `portainer_portainer:9000`.
- Swarm membership: `vm100-prod` changes from worker to manager.
- Verify manager quorum, Portainer/Agent replicas, `/api/status`, LAN route
  access, and that public exposure remains blocked.

## Deployment evidence

- Swarm managers: `rpivn` is `Leader`; `vm100-prod` is `Reachable`.
- Portainer services: Agent `4/4`, Server `1/1`, Portainer CE `2.45.3`.
- LAN checks: `/api/status` and `/` return HTTP 200 through the Pi5 route.
- Public-path check: the VPS address does not expose the Portainer route.

## Redeploy evidence — 2026-10-31

The Portainer Server task was redeployed from the committed stack manifest
without deleting `portainer_portainer_data`. The replacement task is Running
on `rpivn`; three consecutive LAN probes returned HTTP 200 in under 0.1s, and
all four Agent tasks remained Running. No startup error, timeout, or connection
failure appeared in the recent service logs.

## Access correction — 2026-10-31

The Portainer route returned `403` for a client reaching Pi5 through the
NetBird overlay. The route remains LAN-only, with the private NetBird range
`100.69.0.0/16` added to the existing local-network allowlist; public traffic
is still rejected.
