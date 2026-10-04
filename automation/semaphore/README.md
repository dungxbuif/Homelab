# Semaphore UI pilot

This directory defines the private operator UI for the homelab backup control
plane. The current Swarm stack is a Pi5 pilot, not the final production runner.
The deployment record is [here](../../docs/deployments/semaphore-backup-ui-2026-10-04.md).

## Placement and access

- Stack/service: `semaphore_semaphore`
- Image: `semaphoreui/semaphore:v2.19.12`
- Metadata: local SQLite file under `/ssd-data/infra/semaphore/data`
- Network: existing external Swarm network `homelab-net`
- Host ports: none
- Ingress: Pi5 Traefik file provider, LAN/NetBird-only middleware

The pilot is intentionally limited to UI and no-op job verification. Do not add
database provisioning, Google Drive credentials, restic passwords, or production
schedules until the runner and secret boundary are moved to VM100.

## Secret files

Create these files on the target host with mode `0600`, then import them as Docker
Swarm secrets; never commit them:

```text
secrets/admin_password
secrets/access_key_encryption
```

The access-key value must be a 32-byte base64 value. The admin password is
generated outside Git and is not printed by the deployment procedure.

## Smoke test

After starting the stack, verify:

```bash
docker service ls --filter name=semaphore_semaphore
docker service logs --tail=80 semaphore_semaphore
curl -fsS https://semaphore.dungxbuif.com/api/ping
```

The hostname is private-only and must not be added to the VPS public route. A
successful smoke test means the UI loads, login works, and a no-op project/task
can be created. It does not mean production backups are active.
