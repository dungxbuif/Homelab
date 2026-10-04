# Semaphore Backup UI Pilot

**Date:** 2026-10-04
**Status:** Deployed as a private pilot; production backup schedules are still disabled

## Runtime

| Item | Value |
|---|---|
| Host | Pi5 `rpivn` / `10.10.0.5` |
| Runtime | Docker Swarm service `semaphore_semaphore`, `1/1` |
| Image | `semaphoreui/semaphore:v2.19.12` (`sha256:399680...`) |
| Metadata | SQLite at `/ssd-data/infra/semaphore/data` |
| Network | Existing `homelab-net` overlay; no host port published |
| Route | `https://semaphore.dungxbuif.com` through Pi5 Traefik |
| Access policy | Traefik `lan-only`: `10.10.0.0/24`, `10.66.66.0/24`, `10.0.0.0/24` |

The service is intentionally a UI-only pilot. It does not yet contain production
database provisioning, Google Drive credentials, restic passwords, or scheduled
backup jobs. The target architecture still moves the runner and durable control
metadata to VM100 after the workflow is validated.

## Secret boundary

The admin password and Semaphore access-key encryption value were generated as
host files and imported into Docker Swarm secrets:

```text
semaphore_admin_password
semaphore_access_key_encryption
```

The admin password is also available to the operator in the gitignored local file
`credentials/semaphore-admin-password`. No secret value is stored in this
repository or in the route configuration.

## Verification

- `docker service ls`: `semaphore_semaphore 1/1`.
- Direct task probe from the Traefik network: `pong`.
- LAN HTTPS `GET /api/ping`: HTTP `200`, body `pong`.
- Admin login: HTTP `204`; authenticated `GET /api/user`: HTTP `200`.
- Authenticated `GET /api/projects`: HTTP `200`.
- Forced VPS address `103.82.21.202`: HTTP `404`, confirming no public route.
- Pi5 Traefik dynamic configuration was backed up before route addition as
  `/home/dungxbuif/edge/traefik/dynamic.yml.bak-semaphore-20261004-232800`.

## Operational notes

Traefik's dynamic file is bind-mounted. Replacing the file inode does not update
the already-running container's view, so a controlled Traefik restart is needed
after this style of route update. The restart was completed after the backup above;
all tested existing routes remained responsive.

## Rollback

Remove only the pilot service and restore the recorded Traefik file if required:

```bash
docker stack rm semaphore
cp /home/dungxbuif/edge/traefik/dynamic.yml.bak-semaphore-20261004-232800 \
  /home/dungxbuif/edge/traefik/dynamic.yml
docker restart edge-traefik-pi5
```
