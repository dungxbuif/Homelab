# Backup control plane transition

Status: approved retirement of legacy schedules; replacement not deployed.

Implementation plan: [DB management control plane](../superpowers/plans/2026-10-23-db-management-control-plane.md).
Custom services use Bun and TypeScript; upstream containers retain their
supported runtimes. CouchBackup under Bun requires compatibility verification.

User approved stopping and cleaning the legacy backup stack before replacement.
All new administration services belong on VM110 (DB operations), including the
control plane, CloudBeaver, Databasus and the proposed Backrest instance.

Safety scope: disable legacy homelab backup timers first. Preserve Google Drive
snapshots, recovery keys, configuration, manifests and the last verified local
artifacts. Do not prune repositories or delete production volumes. Inspect jobs
before deleting staging/cache; never remove an active job's files. Archive old
deployment definitions before uninstalling runtime. Backup coverage is paused
until replacement acceptance; do not describe this interval as protected.

Verification: list installed timers and running services on VM100, VM110 and Pi;
disable only homelab backup timers, confirm inactive/disabled, and record any
unreachable hosts. Do not disable operating-system dpkg backup timers.

CouchBackup candidate: IBM/couchbackup provides native CLI/library export and
restore. Its README explicitly excludes supported attachment backup/restore;
the attachment option is experimental. Audit every CouchDB database before
selection. Preserve security/config/system metadata separately and test isolated
restore, including attachments and LiveSync behavior, before replacing the
existing exporter. Nano remains an administration client, not a backup engine.

Sources: https://github.com/IBM/couchbackup

## Google Drive destination

User-designated root folder (2026-10-23):
https://drive.google.com/drive/folders/1XzEaTjaBnDU0smPxuzkEnw5s2ScRn3OW

Folder ID: `1XzEaTjaBnDU0smPxuzkEnw5s2ScRn3OW`.
Use OAuth from project `homelab-backup-488616`, not the MyPocket project.
Proposed child layout: `databasus-postgres/`, `backrest-couchdb/`,
`backrest-rustfs/`, `backrest-gitlab/`, and `control-plane-recovery/`.
Each backup engine owns retention only within its designated child folder;
never apply recursive root-folder deletion or a second retention engine to the
same repository. Preserve any existing contents until explicitly inventoried.

This records the destination only: access, quota, child folders and runtime
configuration have not been verified or changed. Before enabling schedules,
verify the authenticated account can create/read/delete a disposable test
artifact in the designated child folder and complete backup/restore acceptance.

Public documentation: no public behavior changed; this is an internal migration.

## Execution evidence

- VM100: all nine installed homelab-backup timers disabled with `--now`;
  zero running homelab-backup units after the change.
- VM110: all eight installed homelab-backup timers already disabled;
  zero running homelab-backup units. SSH succeeded with IdentitiesOnly.
- Pi SSH probe completed: timer listing matched only the operating-system
  dpkg-db-backup timer, which was left unchanged. Cron/container schedules have
  not yet been exhaustively inventoried.
- No snapshots, keys, caches or runtime files deleted yet. Cleanup remains
  pending inventory; replacement backups are not enabled.
