# Monthly restore drill

## Decision

VM100 will run one unattended restore drill on the first day of each month.
The drill uses the existing Restic repositories and `restore-staging.sh`; it
does not create a second backup pipeline and never restores over a production
path.

The first implementation restores the newest snapshot for `databases`,
`database-instances`, `gitlab`, and `rustfs` into a unique disposable run
directory. It verifies the completion marker, manifest status, and every
checksum file present in the restored payload. PostgreSQL/CouchDB and RustFS
application-level smoke tests remain separate acceptance jobs because they
need disposable database/object-store containers and must not silently depend
on production network names.

## Safety contract

- A global backup flock prevents overlap with backup, retention, or health
  work.
- The target is created with a unique run id below
  `/opt/apps/homelab-backup/restore-drills/` and is removed on success or
  failure.
- The job refuses to start below the configured free-space floor.
- It never publishes a host port and never writes to a production volume.
- A success marker is written only after every class passes. A failure removes
  the marker and sends one Mezon failure notification.
- The timer runs after the normal daily backup window, on the first day of the
  month at 14:00 Asia/Ho_Chi_Minh.

## Verification

Source tests cover snapshot selection, marker handling, checksum validation,
lock behavior, cleanup, and the systemd contract. After deployment, the first
run is started manually only while the scheduler is idle; its journal, marker,
Mezon notification, and disk cleanup are recorded in a follow-up evidence
note.
