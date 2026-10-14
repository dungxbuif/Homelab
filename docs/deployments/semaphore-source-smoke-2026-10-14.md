# Semaphore authenticated source smoke

## Intent

Create one read-only Ansible task using GitLab repository 2, the existing
localhost inventory and an empty environment. Preserve template 1 and task
history. Execute on the current local executor first, without enabling global
remote jobs. Require a real checked-out Git commit, the policy file, GitLab TLS
HTTP 200 and private provisioner health status ok. No DB creation, credentials
in repository URLs, host SSH or Docker socket access is needed by the task.

This distinguishes the branch-discovery API's HTTP 400/git exit 128 from the
actual authenticated task checkout. It is not a full host audit or production
deployment test. Record the task ID and verified result after execution.
Only internal operational docs change; there is no public app behavior change.
