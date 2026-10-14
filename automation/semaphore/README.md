# Semaphore Control Plane Pilot

This directory defines the private operator UI for the homelab backup control
plane. The current Swarm stack is a Pi5 pilot, not the final production runner.
The deployment record is [here](../../docs/deployments/semaphore-backup-ui-2026-10-04.md).

## Placement and access

- Stack/service: `semaphore_semaphore`
- Image: `semaphoreui/semaphore:v2.19.12`
- Metadata: local SQLite file under `/ssd-data/infra/semaphore/data`
- Job repository: private local Git repository under `/ssd-data/infra/semaphore/repository`
- Network: existing external Swarm network `homelab-net`
- Host ports: none
- Ingress: Pi5 Traefik file provider, LAN/NetBird-only middleware

The UI remains private and unprivileged. It has one narrowly scoped
`homelab_provisioner_token` secret so the `db-provision` template can call the
internal provisioner API; it still does not mount the Docker socket. Google
Drive credentials, restic passwords, and production backup schedules remain
outside the UI pilot.

## Automation control plane

Semaphore is the only operator entry point for host audits, Ansible checks and
applies, OpenTofu plans and approved applies, route publication, application
deployment, and rollback. The declarative catalog is in
[`project-resources.yaml`](./project-resources.yaml) and the template contracts
are in [`templates/`](./templates/).

The roles are deliberately narrow:

| Role | Allowed work |
|---|---|
| `Viewer` | Read-only host audit, Ansible check, and OpenTofu plan |
| `Task Runner` | Read-only work plus route/app/rollback workflows that still require their declared approval gate |
| `Manager` | All workflows, including production apply and OpenTofu apply |

Every template fixes the repository revision, inventory/workspace, allow-listed
variables, execution image reference, approval boundary, and post-check. The
execution image is resolved from `AUTOMATION_EE_IMAGE_DIGEST`; mutable tags are
rejected. Apply templates require a reviewed plan artifact and `Manager`
approval.

The current repository is expected to be the private GitLab project
`dungbuif/homelab-automation`. Until that project is authenticated and the
image digest is published, these files are a versioned contract and must not be
imported as production templates with a guessed image reference.

## Secret files

Create these files on the target host with mode `0600`, then import them as Docker
Swarm secrets; never commit them:

```text
secrets/admin_password
secrets/access_key_encryption
```

The access-key value must be a 32-byte base64 value. The admin password is
generated outside Git and is not printed by the deployment procedure.

Semaphore keeps the existing `db-provision` template for database/user
provisioning and adds the operator catalog above. Backup scheduling is not
owned by this UI. The canonical serial runner is in
[`../backup-runner/`](../backup-runner/) and its schedules are defined by the
runner/systemd deployment, so there is no second schedule template to import
or maintain here.

The `db-provision` playbook is in `playbooks/db-provision.yml`. It accepts only
the request fields documented in the database provisioning runbook. Generated
credentials are written by the provisioner to Swarm secrets and are never
returned in the task output.

The UI template survey definition is kept in
[`templates/db-provision.yaml`](./templates/db-provision.yaml). The form uses
`database_name` and `target_environment` because `name` and `environment` are
reserved Ansible variables; the playbook maps them to the API request keys
`name` and `environment`.

## Smoke test

After starting the stack, verify:

```bash
docker service ls --filter name=semaphore_semaphore
docker service logs --tail=80 semaphore_semaphore
curl -fsS https://semaphore.dungxbuif.com/api/ping
```

The hostname is private-only and must not be added to the VPS public route. A
successful smoke test means the UI loads, login works, and a disposable staging
database can be created, smoke-tested, and removed. It does not mean production
backups are active.
