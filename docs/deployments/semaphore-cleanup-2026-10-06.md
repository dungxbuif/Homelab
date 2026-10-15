# Semaphore Cleanup

**Date:** 2026-10-06
**Status:** Completed

## Decision

Semaphore is a private database-provisioning UI, not a second backup scheduler.
Keep exactly one project and one task template:

- project: `Homelab Control Plane`
- template: `db-provision`
- backend: private `homelab-provisioner` on `homelab-net`

Backup schedules remain owned by the canonical runner and systemd timers. The
unused Semaphore schedule template is not imported and will be removed from the
source tree. Semaphore task history is operational UI metadata; old failed
probe tasks may be cleared after the SQLite database is copied aside.

## Canonical runtime

- database/provisioner code: `/ssd-data/infra/backup-runner/app/backup/`
- backup runner: `/ssd-data/infra/backup-runner/app/automation/backup-runner/`
- Semaphore source repository: `/ssd-data/infra/semaphore/repository/`
- Semaphore metadata: `/ssd-data/infra/semaphore/data/database.sqlite`

The old top-level Pi copies of `backup-runner`, `gitlab-backup`, and
`rustfs-backup`, plus the copied provisioner playbook and unused Semaphore
schedule file, are not runtime inputs and are removed during this cleanup.

## Safety and verification

Before cleanup:

1. Confirm the live Swarm service and mounts.
2. Confirm the Semaphore database contains one project and one template.
3. Copy the SQLite database before removing task history.
4. Confirm no systemd unit, stack file, or container references the legacy paths.

Completed cleanup:

1. The SQLite database was copied to
   `/ssd-data/infra/semaphore/data/database.sqlite.precleanup-20261006-222206.sqlite`.
2. Six old task records and their output/stage rows were removed; the project
   and the single `db-provision` template were retained.
3. The live `semaphore_semaphore` and `homelab-provisioner_provisioner` services
   remain `1/1` with no published provisioner port.
4. The old duplicate runtime directories and unused Compose/schedule/playbook
   files were removed from the Pi after confirming there were no references.
5. The canonical runner and inventory contract tests pass in the repository.

The SQLite safety copy is retained until the next verified Semaphore backup
window, then may be removed manually after confirming the UI and provisioner
remain healthy.
