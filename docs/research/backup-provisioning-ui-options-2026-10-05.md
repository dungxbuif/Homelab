# Backup and Database Provisioning UI Options

## Decision

Keep the homelab control plane as a small composed open-source stack:

- **Semaphore UI** is the private operator UI, API, job history, approval and
  schedule surface.
- **Ansible** performs idempotent database/user/bucket provisioning and updates
  the catalog only after the native operation succeeds.
- **The catalog** is the single source of truth for active database and bucket
  coverage. Every backup run reads it, so a resource created through the UI is
  included on the next scheduled run without editing backup scripts.
- **Native exporters** remain engine-specific: PostgreSQL/CouchDB logical
  exports, GitLab native backup, and RustFS S3 object export.
- **Restic through rclone** encrypts, versions and transports the completed
  class artifacts to the three Google Drive repositories.

The UI workflow for a new application is:

1. The operator submits an application, engine/resource names, owner identity,
   environment, policy ID and secret reference.
2. The job validates names and policy, creates the database/user or bucket
   idempotently, and runs a connectivity smoke test.
3. The job atomically registers the successful resource in the catalog. The
   catalog contains metadata and secret references only, never passwords.
4. The next backup run discovers the new resource from the catalog, exports it,
   uploads it, runs the post-check, and reports the result to Mezon.
5. A nightly drift audit compares live resources with the catalog and reports
   anything created outside the UI.

This preserves one operational workflow for PostgreSQL, CouchDB and RustFS
without pretending that GitLab application data is a generic database.

## Options considered

### CloudBeaver

CloudBeaver is useful as a private database browsing/query UI, but it is not
the provisioning, policy, catalog or multi-engine backup controller. If added,
it should be a read-mostly operator tool behind LAN/NetBird, not a second path
that bypasses the catalog.

### Databasus / PG Back Web

These are interesting self-hosted PostgreSQL backup UIs with cloud destinations
and notifications. They do not cover the homelab's CouchDB, RustFS and GitLab
backup contracts, and introducing one would create a second PostgreSQL backup
source of truth. Revisit only if PostgreSQL point-in-time recovery becomes a
requirement.

### Bytebase

Bytebase is a strong addition for schema change review, access governance and
database-as-code. It is not a replacement for instance provisioning or the
native backup adapters. Add it later for migration review if schema governance
becomes the next bottleneck.

### pgBackRest

pgBackRest is the right next layer when PostgreSQL needs physical/incremental
backups and point-in-time recovery. The current per-database logical export is
easier to restore selectively and matches the present lab requirement; adding
pgBackRest now would increase operational surface without improving the other
backup classes.

## Sources

- [Semaphore UI documentation](https://semaphoreui.com/docs)
- [Semaphore getting started and schedules](https://semaphoreui.com/docs/getting-started)
- [CloudBeaver documentation](https://dbeaver.com/docs/cloudbeaver/)
- [Databasus project](https://github.com/databasus/databasus)
- [Bytebase project](https://github.com/bytebase/bytebase)
- [pgBackRest documentation](https://pgbackrest.org/command.html)
