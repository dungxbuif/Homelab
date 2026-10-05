# Database Provisioning Runbook

## Contract

Every new application database is created as one declarative unit:

1. A dedicated database/document namespace.
2. A dedicated application owner identity.
3. A backup policy reference.
4. A secret reference for the generated credential.
5. A catalog entry containing no password.

The operator chooses the engine, name, application, environment, owner
identity, policy, and secret reference. The UI/job accepts no arbitrary SQL and
does not accept an inline password.

## Automatic backup enrollment

The private Semaphore `db-provision` workflow is the supported creation path.
Semaphore sends the validated request to the internal `homelab-provisioner`
service; the UI itself has no Docker socket and no database credentials. After
the native create and connectivity smoke test succeed, the provisioner
atomically adds the resource to the canonical backup catalog. A failed
provision will never create an inventory entry. The next database backup run
reads that catalog, so no backup script or schedule edit is needed for a newly
created application.

The catalog stores the engine, resource name, application, lifecycle, policy ID,
and secret reference only. A nightly drift check compares live resources with
the catalog and reports resources created outside the UI. Retiring a resource
changes its lifecycle and preserves its historical backup records.

The current pilot is on Pi5: open `semaphore.dungxbuif.com` from LAN or
NetBird, choose the `Homelab Control Plane` project and run the `db-provision`
template. The form fields `database_name` and `target_environment` are mapped
to API keys `name` and `environment`; this avoids Ansible's reserved variable
names. When starting a task through the Semaphore API, pass survey values as a
JSON string in the task `environment` field. The provisioner API itself remains
internal and is not routed through Traefik or the VPS.

Example request:

```json
{
  "engine": "postgresql",
  "name": "notes_staging",
  "application": "notes",
  "environment": "staging",
  "owner_role": "notes_app",
  "policy_id": "db-default",
  "secret_ref": "swarm:notes-db"
}
```

Validate it before a Semaphore job is allowed to run:

```bash
python3 backup/scripts/validate_provision_request.py \
  --request backup/provision-request.example.yaml \
  --inventory backup/inventory.yaml \
  --policies backup/policies.yaml
```

## PostgreSQL behavior

The executor creates the role and database idempotently, makes the role the
database owner, revokes default `PUBLIC` database access, and grants only the
application permissions required by the selected template. Application roles
must not receive `SUPERUSER`, `CREATEDB`, or `CREATEROLE`. Backup uses a
separate backup credential and the globals export, not the application role's
password.

The first production use must run with a `staging` name and verify an
authenticated `SELECT 1` plus the application connection before promotion.
Rerunning the same request is allowed; destructive drop/rename operations are
not part of this workflow.

## CouchDB behavior

The executor creates a named database, a named user/member, and the database
`_security` policy through the authenticated CouchDB API. System databases
such as `_users`, `_replicator`, and `_global_changes` cannot be provisioned
through this flow. A staging request must verify an authenticated read and
the resulting security policy.

## Credential handling

The generated credential is written to the referenced Docker/secret-manager
boundary and is shown only through the operator's approved secret workflow.
It is never printed in job logs, committed to Git, or copied into the catalog.
Credential rotation is an explicit operation; a normal idempotent rerun does
not silently rotate a live application's password.

The first pilot uses `swarm:<secret-name>` references. A new credential is
generated in memory and written directly to a Swarm secret; the value is never
returned in the API response or job log. If the secret already exists, the
workflow will not rotate it implicitly. Production backup schedules remain
unchanged while this provisioning path is verified with disposable staging
requests.
