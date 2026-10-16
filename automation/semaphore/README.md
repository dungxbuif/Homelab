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

OpenTofu VM100 templates have an explicit source-level runtime contract in
[`project-resources.yaml`](./project-resources.yaml). A controlled Semaphore
environment must inject `TF_VAR_proxmox_api_token`,
`TF_VAR_state_encryption_passphrase`, and a readable pinned `SSL_CERT_FILE`,
and provide the `pve` host mapping to `10.10.0.20`. These are environment
secrets/files, not survey variables. The templates also require the observed
VM name and initialize OpenTofu non-interactively. This contract is tested in
Git; it is not evidence that a live Semaphore environment has been enrolled.

## Automation control plane

Semaphore is intended to become the operator entry point for host audits, Ansible checks and
applies, OpenTofu plans and approved applies, route publication, application
deployment, and rollback. The declarative catalog is in
[`project-resources.yaml`](./project-resources.yaml) and the template contracts
are in [`templates/`](./templates/).

The proposed roles are deliberately narrow, but Semaphore Community does not
enforce them as per-template roles. The live boundary is therefore split into
an owner-only production project and a separate read-only audit project:

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

`Homelab Audit` is live as project 2. It contains only the read-only source
checkout, fixed-command host audits for VM100 and Pi5, and combined backup
health. It has one member (`admin`, owner) and no provisioner, release, route,
Docker, OpenTofu, database-provisioning, or application-deployment credential.
Bootstrap it with `node bootstrap-audit-project.mjs --apply`; the script is
idempotent, dry-run safe, and fails on duplicate names or resource drift. A
successful task is required to verify the checkout and forced command path.
This project boundary is not a substitute for non-admin denial tests.

`app-deploy` and `rollback` are currently design-only contracts. Their generic
executor scripts are intentionally absent, so they are not exposed through any
operator role and must not be imported as runnable Semaphore templates. A
service-specific adapter must be implemented and reviewed before either
workflow is enrolled. The live application release boundary is the dedicated
Homepage template; this prevents a form from implying that arbitrary Swarm or
Compose services can already be deployed safely.

The private GitLab project `dungxbuif/homelab-automation` now exists and CI runs
on VM100. The production runner and restricted observer/backup templates are
active. Homepage template 6 is the only enrolled application release path; its
dedicated Mezon notification Variable Group was accepted by live task 56.
Pi5 backup-client template 7 is also enrolled, but its scope is limited to the
lock-aware five-file runtime release described in the backup-client runbook. It
is not an application deployer and it has no VM100 write credential.
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

The Semaphore runner candidate is intentionally not part of the default
production image pipeline. It is built only by the explicit
`BUILD_SEMAPHORE_RUNNER_CANDIDATE=true` CI variable and must pass the same
non-bypassable vulnerability gate before publication or enrollment. The
current vendor runner candidate is blocked by unresolved HIGH findings; the
existing production runner remains unchanged until a patched vendor build or
an approved executor redesign is available.

Semaphore currently keeps the existing `db-provision`, observer, backup-health,
Pi5 backup-client release and Homepage release templates; the generic app
catalog above has not been deployed. Backup scheduling is not owned by this UI.
The canonical serial runner is in
[`../backup-runner/`](../backup-runner/) and its schedules are defined by the
runner/systemd deployment, so there is no second schedule template to import
or maintain here.

The enrolled backup-client release is template 7, `Release backup client (Pi5)`.
It uses a dedicated SSH key and a Pi5-only inventory. The playbook stages the
reviewed five-file bundle, acquires the existing backup lock, verifies hashes,
and leaves a receipt on the target. Set the explicit approval variable required
by the template before running it. The playbook also writes the sanitized
`artifacts/backup-client-release.json` result used by the Semaphore post-check.
A successful task proves client installation and post-check only; it does not
prove a complete Google Drive restore.

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
