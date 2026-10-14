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

Semaphore is intended to become the operator entry point for host audits, Ansible checks and
applies, OpenTofu plans and approved applies, route publication, application
deployment, and rollback. The declarative catalog is in
[`project-resources.yaml`](./project-resources.yaml) and the template contracts
are in [`templates/`](./templates/).

The proposed roles are deliberately narrow (not yet enforced by these files):

| Role | Allowed work |
|---|---|
| `Viewer` | Read-only host audit, Ansible check, and OpenTofu plan |
| `Task Runner` | Read-only work plus route/app/rollback workflows that still require their declared approval gate |
| `Manager` | All workflows, including production apply and OpenTofu apply |

Each design contract declares the repository revision, inventory/workspace, allow-listed
variables, execution image reference, approval boundary, and post-check. The
execution image is resolved from `AUTOMATION_EE_IMAGE_DIGEST`; mutable tags are
rejected by the contract tests. The intended apply workflow requires a reviewed
plan artifact and `Manager` approval; those tests do not enforce live UI access.

The private GitLab project `dungxbuif/homelab-automation` now exists and CI runs
on VM100. Image publication and runner integration are still in progress.
These files are versioned contracts, not native Semaphore API import payloads.
The installed Community version has no per-template Docker executor: an
`execution_image` field here does not select a runtime image in the live UI.
See the [compatibility decision](../../docs/deployments/semaphore-executor-compatibility-2026-10-14.md)
for the pinned whole-runner-container approach and migration gates.

## Secret files

Create these files on the target host with mode `0600`, then import them as Docker
Swarm secrets; never commit them:

```text
secrets/admin_password
secrets/access_key_encryption
```

The access-key value must be a 32-byte base64 value. The admin password is
generated outside Git and is not printed by the deployment procedure.

Semaphore currently keeps only the existing `db-provision` template for database/user
provisioning; the operator catalog above has not been deployed. Backup scheduling is not
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
