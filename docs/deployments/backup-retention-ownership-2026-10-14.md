# Backup retention ownership repair

## Evidence and decision

VM100 reports last databases/RustFS/GitLab units successful on October 13 UTC,
but retention exited 1 at 23:53 UTC. Its journal shows permission denied while
removing old RustFS staging. Pi stat confirms the run directory belongs to
dungxbuif (0775), while the nested objects directory belongs to root (0755).
The AWS CLI Docker invocation uses its default root UID on a writable bind mount.

Run the export writer with the invoking host UID/GID and HOME=/tmp so new
objects are owned by the same account that verifies and retires them. Keep
existing native S3 CLI export and remote verification gates. Preserve the
existing stdout/stderr fix in the dirty exporter. Validate command construction,
real numeric-user AWS CLI execution, then deploy only the exporter after checking
the live source diff. Repair old staging ownership only with an explicit bounded
path check; do not touch live RustFS storage or delete data in this repair.

Also bound backup journal collection to 20 seconds, since the old broad unit
query remained active for 57 seconds before being terminated during audit.
Failure or timeout must remain a failed audit, not an empty successful report.
Public application docs are unaffected by these internal backup changes.

## Deployed and verified

- Live exporter SHA256 before deployment matched the local pre-fix file exactly.
  Installed the UID/GID fix with Ansible's rollback copy enabled.
- AWS CLI 2.17.60 runs on Pi with UID/GID 1004. A real container wrote an
  isolated fixture with that ownership, and the unprivileged host account
  deleted it successfully. No S3 objects were modified by the probe.
- Repaired 13 `rustfs-*` staging directories under the fixed staging root.
  An exclusive backup lock is opened as the backup account before sudo;
  opening the user-owned lock as root failed on the first repair attempt.
  `find -xdev` visits only regular files/directories and does not follow links.
  Verification found no remaining root-owned payload in those runs.
- 27 Python backup tests pass; playbook lint passes. Existing remote snapshots
  and live RustFS data were not deleted or changed.
- Full retention has NOT been rerun. Its failed systemd status is deliberately
  retained. Remote integrity/prune and final cleanup still need an end-to-end
  successful run; some old partially deleted directories may lack COMPLETE and
  require separate recovery-aware cleanup, not unconditional deletion.
- All five VM100 backup timers are scheduled. Next database trigger is
  2026-10-14 18:00 UTC, retention 22:30 UTC.
- Exact journal unit selection returns quickly, but the requested notification
  markers are absent (exit 1). Audit correctly does not certify remote backups.

Docker upgrade authorization arrived during this repair. Proceed with VM100
upgrade preflight next; do not clear retention failure to manufacture success.
