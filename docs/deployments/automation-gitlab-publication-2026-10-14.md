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

## Published state

- Source snapshot: `56ad21690e2a85e2af2643c0ef4f42bd29d8a888`.
- GitLab branch: `codex/automation-bootstrap`.
- GitLab commit: `46117ec94218cfe109abe90fc5312baf22956671`.
- Parent is the remote starter commit; no old source Git history was uploaded.
- Pipeline: https://gitlab.dungxbuif.com/dungxbuif/homelab-automation/-/pipelines/1
- Job 1 is pending/stuck: GitLab explicitly reports no active eligible runner.
  This is not a running build or a CI success.
- Main and the existing Semaphore provisioning job remain unchanged.

Snapshot Gitleaks findings are present in historical manifests and documentation.
These files were retained under the owner's explicit self-hosted upload consent;
the snapshot is not secret-clean and must remain private. Local credential files
and old history are excluded. Route render and ShellCheck error gates passed.

Next gate: install a dedicated CI executor, without sharing the production Docker
socket with jobs, and verify registry publication by manifest digest. A runner
registration alone is insufficient; pipeline 1 must actually finish successfully.
The working publication checkout is `/tmp/homelab-gitlab-publish.AUAqzN`; its
commit is safely stored on GitLab, so loss of this temporary checkout is harmless.
