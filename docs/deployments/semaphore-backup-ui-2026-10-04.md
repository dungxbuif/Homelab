# Semaphore Control Plane Pilot

**Date:** 2026-10-04 (updated 2026-10-06)
**Status:** Private database-provisioning control plane is deployed. Backup
scheduling is now owned by the active VM100 systemd runner; Semaphore remains
UI/provisioner only.

> The original rollout record below is retained as history. For the current
> task history, labels, image versions, and verification state, see [Semaphore
> History and Metadata Recovery](./semaphore-recovery-2026-10-13.md) and the
> [runtime inventory](./runtime-inventory-2026-10-13.md).

## Runtime

| Item | Value |
|---|---|
| Host | Pi5 `rpivn` / `10.10.0.5` |
| Runtime | Docker Swarm service `semaphore_semaphore`, `1/1` |
| Image | `semaphoreui/semaphore:v2.19.12` (`sha256:b85760f41eac1964a89b830aee9e6240a3bdee804b27ce689beeea49c6082103`) |
| Metadata | SQLite at host `/ssd-data/infra/semaphore/data`, mounted as `/var/lib/semaphore` |
| Network | Existing `homelab-net` overlay; no host port published |
| Route | `https://semaphore.dungxbuif.com` through Pi5 Traefik |
| Access policy | Traefik `lan-only`: `10.10.0.0/24`, `10.66.66.0/24`, `10.0.0.0/24` |

The companion service `homelab-provisioner_provisioner` runs `1/1` on the Pi5
leader with image `homelab/provisioner:20261005`. It has no published port and
is attached only to `homelab-net`; the private API listens on port `8787` for
Docker-network clients. It is the only component that mounts the Docker socket.
Semaphore has no Docker socket and calls the provisioner with the external
Swarm secret `homelab_provisioner_token`.

The configured Semaphore project is `Homelab Control Plane` (project `1`) with
the `db-provision` template (template `1`). The template accepts PostgreSQL or
CouchDB metadata, creates the native resource and least-privilege owner, writes
the generated credential to a Swarm secret, runs an authenticated smoke test,
and then enrolls the resource in `backup/inventory.yaml`. The generated secret
value is never returned in API responses or task output.

This is still a pilot. It does not yet contain Google Drive credentials, restic
passwords, or scheduled production backup jobs. The final backup runner and
durable control metadata move to VM100 after this workflow is accepted.

## Secret boundary

The admin password and Semaphore access-key encryption value were generated as
host files and imported into Docker Swarm secrets:

```text
semaphore_admin_password
semaphore_access_key_encryption
homelab_provisioner_token
```

The admin password is also available to the operator in the gitignored local file
`credentials/semaphore-admin-password`. No secret value is stored in this
repository or in the route configuration.

## Verification

- `docker service ls`: `semaphore_semaphore 1/1`.
- `docker service ls`: `homelab-provisioner_provisioner 1/1` with no published port.
- Direct task probe from the Traefik network: `pong`.
- LAN HTTPS `GET /api/ping`: HTTP `200`, body `pong`.
- Admin login: HTTP `204`; authenticated `GET /api/user`: HTTP `200`.
- Authenticated `GET /api/projects`: HTTP `200`.
- Semaphore task `5` provisioned a disposable PostgreSQL staging resource and
  returned success; a rerun was idempotent (`changed=false`). The database,
  role, Swarm secret, and catalog row were removed after the probe.
- Semaphore task `6` provisioned a disposable CouchDB staging resource and
  returned success. The database, `_users` document, Swarm secret, and catalog
  row were removed after the probe; follow-up checks returned database/user
  `404` and zero catalog matches.
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
docker stack rm homelab-provisioner
cp /home/dungxbuif/edge/traefik/dynamic.yml.bak-semaphore-20261004-232800 \
  /home/dungxbuif/edge/traefik/dynamic.yml
docker restart edge-traefik-pi5
```
