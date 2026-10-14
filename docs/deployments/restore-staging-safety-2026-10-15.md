# Restore staging safety gate

Before remote restore rehearsal, repair `backup/scripts/restore-staging.sh`:
the current `mkdir -p` accepts existing directories and can overwrite files.
Require an exact 64-character snapshot ID, an absolute destination, and an
exclusively created new leaf directory under an existing parent. Reject existing
directories/files/symlinks (including dangling links) before sourcing remote
credentials. Keep partial restore data on failure for diagnosis; do not retry
into that directory or automatically remove it. Set mode 0700 on new staging.

Validate with subprocess tests using fake timeout/Docker only: no production
credentials, network, or storage. Then use the guard for a separately recorded
real snapshot restore. This safety test is not proof that remote payloads restore.
Internal operator docs only; no public app contract changes.

## Operator use

Load the approved host-local runtime environment, then run:

```bash
bash backup/scripts/restore-staging.sh databases FULL_64_HEX_SNAPSHOT_ID /approved/restore-parent/new-run
```

The parent must already exist. Do not use `latest`, a snapshot prefix, an
existing empty folder, or a production data directory. If the attempt fails,
inspect its new staging folder and choose a different new folder for a retry.
This exports files only; it does not restore into a running database.

Regression verification: three tests failed before the change (existing target,
permissions, relative target); all four staging tests and 42 backup Python tests
pass afterward. Docker and Drive were replaced by test doubles in these tests.
Install the updated helper on Pi/VM100 with file backup and shell syntax
validation; do not restart jobs or run a remote restore alongside the current
scheduled database backup.

Installed on both hosts via Ansible copy with per-file rollback backups and
`bash -n` validation. Ownership stayed dungxbuif (Pi) and ubuntu (VM100).
ShellCheck with the sourced library passed; separate assignment/export now
preserves a failed destination resolution status. No remote payload restore
was started and no existing staging data was removed.
