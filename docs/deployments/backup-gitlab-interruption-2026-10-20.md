# GitLab backup interruption: 2026-10-20

## Finding

The GitLab backup alert at 20:11 UTC on 2026-10-20 was an operator/deployment
interruption, not a PostgreSQL, Restic, or Google Drive data failure.

The VM100 journal records:

```text
sudo ... systemctl stop homelab-backup@gitlab.service
homelab-backup@gitlab.service: Main process exited, code=killed, status=15/TERM
```

The service was stopped while the GitLab native export was running so the
Restic upload helper could be replaced. The subsequent recovery check found
the remote snapshot for `gitlab-20261020-190208`, and the next scheduled run
completed successfully.

## Evidence

- GitLab run `gitlab-20261020-190208` completed with a remote snapshot.
- The next live health checks reported `gitlab.success_age` and a free lock.
- VM100 currently has no failed backup units and has about 37 GB free.
- The interruption happened before the release/install commands recorded in
  the same journal window, so it is classified as a controlled deploy stop.

## Operational correction

Backup runtime publication must refuse to stop an active backup unit. A helper
replacement is scheduled only after the unit is idle; if an emergency stop is
unavoidable, the operator must run the class to completion and verify the
success marker before resetting the failed unit. A `SIGTERM` during a backup
is still a failed run and remains visible in incident history.

This incident does not change the restore acceptance result. GitLab,
shared PostgreSQL/CouchDB, and RustFS restore drills were independently
verified on 2026-10-21.
