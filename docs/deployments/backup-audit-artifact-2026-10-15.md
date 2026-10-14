# Backup audit evidence contract

The existing backup-audit template claims an artifact that the playbook does
not create, and its capacity probe reads /tmp rather than the staging volume.
Repair before enabling the template in Semaphore. Pi staging is
`/ssd-data/infra/backups/homelab`; VM100 staging is
`/opt/apps/homelab-backup/runs`. Reject other targets.

Produce private per-host JSON on the controller, recording the exact staging
path and observed unit/log evidence. Keep remote snapshot and retention
verification explicitly `not_run`; a read-only audit is not a restore test.
The template passes a controller artifact directory and verifies both host
files, rather than an imaginary combined text file. Verify YAML contract tests,
Ansible lint, then a read-only live run on each host. Restricted runner access
and live UI template registration remain separate pending gates.

Public app docs are unaffected: this is an internal operator audit contract.

## Verification

Regression test failed on the missing staging map, then passed after repair.
A live run exposed that Pi has no scheduler journal; restrict journal reads to
VM100. An empty grep result (rc=1, no stderr) is recorded, not treated as proof
of success. Timeouts/errors still fail collection. Read exact local marker files
for databases/RustFS on Pi and GitLab on VM100 and retain individual read codes.

Both live read-only runs completed: only controller artifact writes reported
changes. Artifacts are under `/tmp/homelab-backup-audit-20261015`, one JSON per
host. All three local markers were readable. VM unit evidence reports three
successful backups and failed retention; remote verification remains `not_run`.
Pi staging filesystem had 300072372 KiB available; VM100 had 68018992 KiB.
This used the documented temporary bootstrap transport, not the final restricted
Semaphore runner. Do not claim UI rollout or controller-only operation complete.

CI pipeline 30 caught an error-handling regression: marker reads had unconditional
`failed_when: false`. Fail collection on any nonzero marker read instead; a
missing or unreadable local marker is evidence of an incomplete audit and must
not pass. Preserve journal's explicit empty-result handling separately. Verify
the full inventory contract suite as well as the narrower artifact tests.
