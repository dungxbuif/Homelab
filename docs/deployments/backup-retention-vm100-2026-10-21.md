# VM100-owned backup retention

Date: 2026-10-21
Status: deployed and verified

## Change

VM100 now owns retention and integrity work for the `databases` and `rustfs`
Restic repositories. Pi5 still performs its data export/upload jobs and
exposes only read-only success markers through the restricted SSH command.
The VM100 runner reads those markers before running local verification and
retention, so stale or missing Pi5 results still fail closed.

The weekly integrity runner on VM100 covers `databases`, `rustfs`,
`database-instances`, and `gitlab` with `RESTIC_READ_DATA_SUBSET=1/10`.

## Evidence

- Semaphore task `#146` released commit `6a51922772a6f739d48ec943a727b466fdd555ee`.
- Pi5 marker export returned successful runs:
  - `databases-20261020-180001`, snapshot
    `45fc58a1c463cb5ec85a008007e26ee1f0e5376d40ee1f858d2afe50436762cb`.
  - `rustfs-20261020-210003`, snapshot
    `667cb32216c6417d1ab9d2b7a6b28d2839d04e5e5b672af8e87329d6b942942c`.
- VM100 live SHA matches the reviewed source:
  `run-vm100-scheduled.sh` `6c122e16...` and
  `run-integrity-check.sh` `019d6cda...`.
- All backup units were inactive during publication; the global lock was free.
- VM100 has about 31 GB free (85% used).
- `databases` was rerun successfully as systemd run
  `databases-20261020-231247`, snapshot
  `8f1d38f77edf34e66f0991dd0482c28028fdd0b7c3faff93a4a3e2a02dd7a670`.
- Retention completed for `databases`, `rustfs`, and GitLab. It removed two
  duplicate/obsolete database snapshots and one old database-instance
  snapshot while preserving the configured daily/weekly/monthly policy.
- A stale lock from an interrupted `database-instances` run was detected only
  after confirming no Restic/rclone process was alive, unlocked, and then
  rechecked/pruned successfully. The health service passed afterward with a
  free global lock.

## Compatibility repair

The VM100 key's `authorized_keys` entry invokes the historical names
`homelab-backup-ssh-guard` and `homelab-backup-executor`. The release playbooks
now publish both those aliases and the newer `pi-ssh-guard.sh`/
`pi-executor.sh` names. A live VM100-to-Pi5 marker request passed after the
aliases were repaired.

## Verification and rollback

The first destructive retention run was observed through its systemd journal
and success markers. The one missing repository class was completed with the
existing `run-instance-retention.sh` wrapper after stale-lock cleanup; no
standalone `restic forget` or `prune` command was run.
The previous VM100 runtime is preserved at the timestamped rollback directory
created during publication. Pi5 handler files also retain the release-tool
rollback copies.
