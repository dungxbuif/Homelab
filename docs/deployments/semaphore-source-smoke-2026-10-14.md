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

## Verified local executor result

Task 7 succeeded using template 2 and GitLab repository 2 at commit
`4e8d4645edbc1db1808d2727fcf27a68f2b4b0f0`: 7 tasks OK, 0 changed, 0 failed.
Authenticated checkout, private provisioner health and GitLab HTTPS passed.
This ran on the UI's local executor, not the VM100 remote runner. The separate
repository branch-list API still returns HTTP 400; successful task checkout
does not prove that dropdown works.
