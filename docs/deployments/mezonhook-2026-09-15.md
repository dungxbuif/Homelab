# MezonHook Swarm Cutover - 2026-09-15

## Runtime

- Old Compose project `mezonhook`, container `vm100-mezonhook`, image
  `homelab/mezonhook:vm100-20260911` (VM100 image ID
  `sha256:9f2bcbce8bcb5c73ac44d1f79445129eabae9b9d356f9b3a4960f401e0f8e497`).
- New Swarm service `mezonhook`: one replica constrained to VM100, on
  `homelab-net`, no published port, no mounts/application environment.
- Healthcheck: `wget -qO- --timeout=3 http://127.0.0.1:8080/`, 30s interval,
  5s timeout, three retries; task healthy.
- Orange Pi file route: `mezonhook@file` -> `http://tasks.mezonhook:8080`.
- Old Compose container stopped at 13:50:21 UTC. VM100 port `18084` has no
  listener; Compose YAML and image remain for rollback.

## Evidence

- Before source edit, source/live Orange Pi dynamic YAML SHA256:
  `a43abe25c048d934392b90f518eeb140f9a26aa343a919397e61c4e3b2920d0f`.
- Orange Pi backup:
  `/opt/edge/traefik/dynamic.yml.bak-mezonhook-swarm-20260915-134008`.
- After edit, source/live SHA256:
  `6c0c04414d41391146ccc184a7da946bad9c33377b8ebca64bcbe1dbc3ee80ad`.
- Route assertion failed before edit and passed after; YAML parsed. Orange Pi
  canary probe to `tasks.mezonhook:8080` returned 200.
- MezonHook/Homepage/n8n/pgAdmin public probes passed four rounds spaced 15s
  apart, again after more than 10 minutes, and after the Compose stop
  (200/200/200/302). Traefik access log showed the new `tasks.*` target.

## Edge Overlay Incident

At about 13:37 UTC, immediately after the MezonHook canary joined
`homelab-net` and **before** its route changed, Homepage, n8n, and pgAdmin
returned 502 while MezonHook still returned 200 on its old LAN route. A curl
container sharing the existing Traefik task's network namespace could not
connect to `tasks.homepage:80`; that namespace's `/proc/net/arp` showed
overlay destinations with `Flags 0x0` and empty MAC addresses. A fresh Orange
Pi container on `homelab-net` reached Homepage 200 with a resolved `Flags
0x2` ARP entry. After `docker service update --force edge_traefik`, the shared
namespace probe returned 200, ARP entries resolved, and public routes
recovered. This identifies the failing boundary but not the Docker/kernel
mechanism that made the old overlay endpoint lose neighbor resolution.

## Rollback

On VM100:

```sh
docker compose -p mezonhook -f /opt/apps/mezonhook/run/docker-compose.yml start mezonhook
```

Then copy the saved Orange Pi dynamic YAML backup **into**
`/opt/edge/traefik/dynamic.yml` and verify both public and cross-route probes.
If several overlay routes fail simultaneously, investigate/recover the edge
task separately; changing only the MezonHook URL cannot repair that fault.
