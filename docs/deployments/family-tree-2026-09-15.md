# Family Tree Swarm Cutover - 2026-09-15

## Datastore endpoint follow-up

On 2026-09-15, after the Swarm cutover, only the service's `DATABASE_URL`
host/port changed from equivalent Pi5 LAN PgBouncer mapping
`10.10.0.5:5432` to private overlay `pgbouncer:6432`. Database, user,
password, and URL query parameters were preserved. The app's own
`utils/db/client.ts` returned `SELECT 1` against the overlay before and
after update; the new task was healthy and public `/login` returned `200`.
Rollback for this follow-up is to restore only the prior service URL, not
the whole route cutover or any database data.

## Runtime

- Previous Compose project `family_tree`, service `app`, container
  `vm100-family-tree-app`, port `18085:3000`.
- Image: VM100-local `oven/bun:1-slim`, ID
  `sha256:cb3bbbb08e13a4a2ff400f24c7a2a1d5efa83f6ef8544d52d95a519631e2fc61`;
  service creation used `--no-resolve-image` to preserve that local image.
- New service `family-tree`: one replica constrained to VM100, on
  `homelab-net`, no published port. Command `bun run start` from `/app`.
- Bind mounts: `/opt/apps/family-tree/src:/app` and
  `/opt/apps/family-tree/uploads:/app/uploads` (VM100 uploads directory mode
  700). The task and old container had equal image IDs, sorted environment
  values, and mount destinations; env values were streamed through a 0600
  manager-side temporary file and were not recorded in this note.
- Health: existing Bun fetch of `http://127.0.0.1:3000/login`, 30s interval,
  5s timeout, 15s start period, three retries. Task healthy.
- Route: `family@file` -> `http://tasks.family-tree:3000`.
- Previous Compose container stopped at 14:07:59 UTC. Port `18085` had no
  listener afterward; Compose YAML/image/mounts remain for rollback.

## Verification

- Before source edit, source/live Orange Pi dynamic YAML SHA256:
  `6c0c04414d41391146ccc184a7da946bad9c33377b8ebca64bcbe1dbc3ee80ad`.
- Backup: `/opt/edge/traefik/dynamic.yml.bak-family-tree-swarm-20260915-135728`.
- After route edit, source/live SHA256:
  `cc4c087e4c2647bce26946d50cd8f51e2e26cc9a6b0ceae9b2a8a5d5bf8835a4`.
- Route assertion failed before edit and passed after; YAML parsed. Orange Pi
  task probe to `/login` returned 200. Access log showed the new task target.
- Family `/login`, MezonHook, Homepage, n8n, and pgAdmin public probes passed
  four rounds spaced 15s apart, again after more than 10 minutes, and after
  the Compose stop (200/200/200/200/302).
- A real read-only DB query through the task's own `utils/db/client.ts`
  returned `SELECT 1` before and after the old container stopped. Task stayed
  healthy; VM100 source/uploads mounts remained present.

## Edge Overlay Incident

Soon after this canary joined `homelab-net`, and before the Family route
changed, existing overlay routes returned 502 while Family still returned 200
over its old LAN route. In the old Traefik task's network namespace,
`tasks.family-tree:3000` could not connect and overlay ARP entries showed
`Flags 0x0` with empty MACs. A fresh Orange Pi overlay container reached
Family `/login` 200. Replacing only `edge_traefik` restored ARP resolution
and public routes. This repeated symptom localizes the failed endpoint; it
does not prove the exact Docker/kernel defect.

## Rollback

```sh
docker compose -p family_tree -f /opt/apps/family-tree/run/docker-compose.yml start app
```

Then copy the saved Orange Pi dynamic YAML backup **into**
`/opt/edge/traefik/dynamic.yml`, verify source/live hashes, Family `/login`,
DB read, and cross-route probes. Multi-route 502 requires edge-task diagnosis
separately from this single-app route rollback.
