# GitLab runner enrollment

Bootstrap the project-only runner for `dungxbuif/homelab-automation` using the
existing account `dungxbuif`. No new GitLab user or instance runner is needed.
Use a one-day bootstrap API token minted through the administrator transport;
store it only in ignored `credentials/` with mode 0600 and revoke it once
enrollment and verification are complete. Never print tokens in logs.

The runner uses VM100's independent rootless daemon, concurrency 1, project lock,
and no production Docker socket. Its registration token stays in the CI user's
private config. Registration is idempotent by project and description; inspect
existing runners before creating one. Use the modern `/user/runners` API.

Verify runner online, actual pipeline result, registry auth and published image
manifest. Keep the existing provisioning job and production workloads unchanged.
The documented registry-gitlab URL currently returns 404, so registry routing
must be revalidated before claiming publication. Public docs are unaffected.

Runner ID 1 is now online, project_type, locked to project 2, initially paused.
Enrollment rerun reused ID 1 without creating a duplicate. The controller runs
in rootless Docker using image manifest
`sha256:816e7c594a8c319856a710283ed7fba7a9f633cbfe6b167b0632ea3dec101fee`.
The runner controller sees only the rootless socket; job volumes are limited to
`/certs/client` and `/cache`. CI now uses the pinned rootless DinD service.

The authoritative GitLab API reports the image prefix as
`registry-gitlab.dungxbuif.com/dungxbuif/homelab-automation`; Semaphore contracts
were corrected accordingly. The public VPS registry returns the correct 401
Bearer challenge while Pi5 LAN ingress returns 404. Pi5 password authentication
was recovered with the previously supplied password; local_vars' PI5 password
is stale, and agent-based SSH was waiting rather than completing.

The first token-capture attempt was revoked before replacement. The replacement
one-day API token remains required during bootstrap and must be revoked after
CI/registry/Semaphore integration. Do not expose its value in docs or job output.

Pipeline 2 reached the runner but failed starting nested rootless DinD: its
inner UID mapping needs IDs beyond the outer daemon's default 65536 range.
VM100 currently has only ubuntu:100000:65536 and homelab-ci:165536:65536 in
both subordinate maps. Extend only the CI range to 1048576 IDs after verifying
there are no other allocations; preserve its start so existing mapped files
retain ownership. Restart only the CI rootless daemon while the runner is
paused. Keep job privilege restrictions and production daemon untouched.

The expansion applied successfully (`ok=20 changed=2 failed=0`), then runner 1
was unpaused and failed job 3 retried as job 5, confirmed running by the API.
This does not yet prove nested builds succeed. The Pi5 registry LAN route now
returns the expected HTTPS challenge; see `gitlab-registry-lan-2026-10-14.md`.

Further observation: job 5 successfully started the nested rootless daemon,
cloned commit `7ab8a1f`, and began the actual amd64 execution-image build. Its
trace reached the Python dependency installation layer after completing apt
installation. The outer CI user slice and DinD service limits remain the
resource boundary; nested DinD warns that it has no own systemd cgroup manager.
Pipeline 2/job 5 is the live handle to resume, not a reason to restart the build.
Source commit `17c0751` includes the host mapping and registry remediation; it
has not yet been cherry-picked to the publication branch while pipeline 2 runs.

## Verified publication checkpoint

Pipeline 2's scan was found to fail open on Git ownership errors; its build job
4 was canceled before publishing. The corrected scanner passed in pipeline 3,
which completed successfully (validate job 6, build job 7). Registry API confirms
the tag `f805a492867d93f58f3b5ada95fd2959524e8d23` in repository ID 3 with digest
`sha256:3c256fb1d4a4f3ce8d6f738776fd765b668c182987a36072e179b6300cb8a604`.
The compressed image is 162512100 bytes. This verifies CI publication, not live
Semaphore integration or the other automation workflows.

Pipeline 4 at `6e3c4e85baa46a6bd75d4ff732185b02c7e8e0ef` adds the non-root
Semaphore runner image and its real container smoke test. Job 8 was confirmed
running; job 9 is pending validation. Resume these handles rather than rebuilding
from assumptions. The rootless runner is still concurrency one.
