---
type: Deployment Evidence
title: Backup remote repair and database restore acceptance
description: Evidence for the backup/restore gate used before stateful image upgrades
generated:
  by: claude-code/opus-5.5
  at: "2026-10-31T02:03:00+07:00"
---

# Backup remote repair and database restore acceptance — 2026-10-31

This record closes the backup/restore gate for the `databases` backup class.
It does not by itself approve the RustFS, CouchDB, PostgreSQL/pgvector, or
Redis image changes; each service still needs its service-specific backup
check, upgrade, smoke test, and rollback entry.

## Remote repair

- The current custom OAuth client in the Pi5 rclone config returned Google
  Drive `invalid_client`.
- A retained pre-change rclone config authenticated successfully. Its direct
  root was checked before reuse; it contained the legacy `databases/` and
  `databasus_backups/` layout, not the configured `homelab-backups/` root.
- A new `homelab-backups/` folder was created through the authenticated
  remote, and a new Restic repository was initialized under
  `homelab-backups/databases/`.
- The complete local run `databases-20261030-174710` was uploaded with
  snapshot `b1391e30a90fb2048970c3b01bbff07738a25ba0c85cb9a1d4802a5cf5bcd6c0`.
  The upload included the PostgreSQL dumps and the CouchDB export, including
  `obsidian_vault.docs.ndjson` (`820422206` bytes).
- The working config was copied to the official Pi5 path
  `/ssd-data/infra/backup/secrets/rclone.conf` and separately installed on
  VM100 at `/etc/homelab-backup/secrets/rclone.conf`. Both hosts listed the
  new remote root after the change. No credential values are recorded here.
- Before replacement, the VM100 rclone config was preserved at
  `/opt/apps/homelab-backup/runs/version-upgrade-20261031/backup-repair/`.

## Restore evidence

- VM100 restore drill: `restore-drill-version-upgrade-20261031`, class
  `databases`, passed on the current remote. It restored the latest payload,
  verified `manifest.json`, `COMPLETE`, and all recorded SHA-256 checksums.
- PostgreSQL engine check passed from the restored payload: `n8n.dump` was
  restored into a disposable `pgvector/pgvector:pg16` container and
  `SELECT 1` succeeded in `n8n_restore_check`.
- CouchDB engine check passed from the restored payload: `obsidian_vault` was
  restored into a disposable `couchdb:3.3.3` container and the validator
  confirmed `49341` documents in `obsidian_vault_restore_check`.
- The engine-level staging evidence remains at
  `/opt/apps/homelab-backup/restore-drills/engine-version-upgrade-20261031/`
  on VM100. Scratch containers were stopped and removed after validation;
  production volumes were not touched.

## Decision

The `databases` backup/restore gate is **PASS**. The follow-on service checks
also passed for RustFS `1.0.4`, CouchDB `3.5.3`, PostgreSQL/pgvector `16.15`,
and Pi5/RelayHub Redis, with their service-specific archives and smoke results
recorded in the controlled upgrade ledger. GitLab was intentionally skipped
after its native backup grew to multi-GB size. Databasus then received a
separate maintenance follow-up: a fresh `29280340`-byte named-volume archive
was captured, all `15` logical retention values were changed transactionally
from invalid `THREE_MONTH` to source-supported `3_MONTH`, and
`v3.64.0@sha256:dca80ac1…` was applied. Version, health, migrations and the
cleaner startup pass. The Pi5 verification agent was then registered and
started; the post-upgrade n8n backup and the five remaining approved service
database backups all completed successfully with automatic restore
verification. Every approved service row showed `Verified` and `pg_restore`
exit `0`; the per-database evidence is in the controlled upgrade ledger. Other
Databasus jobs remain outside this service-maintenance scope.
