# Automation GitLab publication, 2026-10-14

## Intended change

Publish a snapshot of committed homelab source to private GitLab project
`dungxbuif/homelab-automation`, on `codex/automation-bootstrap`. Preserve the
remote main starter commit as parent; do not push the source repository's old
history or force-update main. Keep the original workspace and its staged and
unstaged backup work unchanged. That backup work is not included in this first
committed snapshot and must be reconciled before production rollout.

Use Git SSH via the verified VPS port 2222. Scan snapshot content and run CI
checks in the execution image. Record the pushed SHA and pipeline status once
available. Publication is not authorization for unattended production apply.

This branch is the review/import boundary. GitLab main and Semaphore's existing
local-file DB-provision job remain unchanged until migration gates pass.
No public app behavior changes; documentation is internal only.
