---
type: Runbook
title: Database Provisioning Runbook
description: Provision a database and owner through Semaphore, then enroll it in Databasus
generated:
  by: claude-code/opus-5.5
  at: "2026-10-31T00:00:00+07:00"
stale_after: "2027-01-29T00:00:00+07:00"
---

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
provision will never create an inventory entry. The restic `databases` class
reads that catalog on its next run; note that this runner currently has **no
schedule** (no VM100 backup timers), so the Databasus job below is the only
scheduled backup for a new PostgreSQL database.

The catalog stores the engine, resource name, application, lifecycle, policy ID,
and secret reference only. A complete nightly live-resource drift check is a
planned gate, not a verified installed capability. Databases created outside
this workflow must be reconciled explicitly; do not assume they were enrolled.
Retiring a resource changes its lifecycle and preserves historical backups.

For a PostgreSQL database in the shared Pi5 cluster, provisioning is incomplete
until the operator also creates a dedicated Databasus job. The job must point to
the exact database name, use the existing Google Drive storage and `Mezon
Homelab` notifier, pass the connection test, and produce a successful first
backup in the `Homelab Backup` Drive folder. Catalog enrollment does not create
this Databasus job automatically.

The current control plane is on Pi5: open `semaphore.dungxbuif.com` from LAN or
NetBird, choose project 1 and run **Provision database and application owner**
(template 1). The form fields `database_name` and `target_environment` are mapped
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

Keep the cluster-level roles and grants in the separate globals backup. After
the first Databasus backup, verify the artifact and complete a restore check
before marking the new database onboarded.

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

The current implementation uses `swarm:<secret-name>` references. A new credential is
generated in memory and written directly to a Swarm secret; the value is never
returned in the API response or job log. If the secret already exists, the
workflow will not rotate it implicitly. Use a staging name for the first request; do not use a destructive
drop/rename operation to “reset” an existing production database.

## Current Semaphore form

The live template is named **Provision database and application owner**. The UI
asks for:

| UI field | Example |
|---|---|
| Database engine | `PostgreSQL` or `CouchDB` |
| Database name | `notes_staging` |
| Application or service | `notes` |
| Target environment | `Staging` |
| PostgreSQL owner role | `notes_app` |
| CouchDB owner identity | `notes_app` |
| Backup policy | `Default database backup` |
| Swarm secret reference | `swarm:notes-db` |

Do not treat Ansible `--check` as a working provisioning preview: the current
playbook's HTTP operation is skipped in check mode and it has no dedicated
validation-only API flow. Use the local validator above for request validation;
normal template execution is the mutating create operation. A successful job
prints the engine, resource name and changed flag, not the generated password
or a full connection string. The project has seven templates and one owner
membership; see the [automation UI guide](automation-operations.md).
Fine-grained operator RBAC and a supported UI preview do not exist yet.
