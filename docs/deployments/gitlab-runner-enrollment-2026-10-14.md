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
