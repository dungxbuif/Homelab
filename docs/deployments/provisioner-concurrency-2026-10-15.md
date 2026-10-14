# Provisioning operation serialization

The threaded HTTP service currently locks only the final catalog registration.
Two requests can therefore race through role/user/secret creation before either
registers the resource. Serialize the entire provision_request operation using
a separate nonblocking advisory file lock next to the canonical catalog.
Acquire before reading the catalog and release only after native smoke and
registration or failure. Never unlink the lock file: replacing its inode would
allow overlapping holders. Reject symlinks/nonregular lock files.

A busy operation returns a sanitized retryable HTTP 409. No request body or
password is stored in the lock. Existing partial-failure secret preservation
remains unchanged. This is serialization, not an atomic cross-system transaction;
external/manual catalog writers and native rollback still require reconciliation.

Tests must prove contention blocks before catalog reads/native writes, lock
release after exceptions, persistent lock inode, and HTTP status semantics.
Deploy only when Semaphore provisioning tasks are idle, with backup copies of
both Python files and a health check. Current backup jobs need not restart.
Internal API/operator docs change; public apps do not consume this private API.

## Source verification and release gate

All three lock regressions failed against the original implementation, then
passed with real file locks. The HTTP fixture verifies sanitized 409 behavior.
46 backup Python tests pass locally and 17 provisioner tests pass inside the
Linux execution image. The server remains unchanged in production: it is baked
into `homelab/provisioner:20261005`, whereas the module is bind-mounted. Updating
only the mounted module would leave the old HTTP status mapping. Publish a new
immutable provisioner image, then coordinate the image/module update with idle
provisioning tasks, preserve rollback artifacts, and repeat real acceptance.
No production DB, user, secret, catalog or service was changed by these tests.

## Immutable image release

Build the HTTP handler and its four Python dependency modules into one image,
using pinned Python and Docker CLI image digests. Copy the static Docker client
from the official CLI image instead of running a package installer: the image
then supports cross-platform ARM64 assembly on the AMD64 rootless CI worker
without privileged QEMU registration. Keep catalog data mounted separately;
SCRIPTS_PATH selects baked modules, never the mutable backup scripts mount.
CI validates native AMD64 imports/client first, then publishes ARM64 for Pi by
commit tag and digest. Only the tested published digest may be rolled out.
No host Docker socket is mounted into build/test containers.

Local ARM64 build completed with a 33.41 kB allowlisted context. With network
disabled and no host Docker socket, Docker client 27.5.1 executes, the server
imports `/app/provisioner/scripts/provisioner.py`, and all 17 provisioner tests
pass. This is a local release candidate test, not proof of CI publication or
production rollout. Live deployment still awaits a published digest.

Rollout through a dedicated Ansible playbook: require explicit approval, idle
Semaphore provisioning tasks, and a registry digest. Pull with temporary scoped
registry credentials, verify baked imports without network or host socket, save
the previous Swarm spec in a mode-0700 receipt directory, then change image and
SCRIPTS_PATH together. Do not overwrite the legacy mounted module: rollback
must retain its previous code. After update, verify health and imported module
location. Roll back only if this invocation actually attempted a spec change;
image-pull/preflight failures must never roll back an unrelated prior release.

`automation/ansible/playbooks/provisioner-release.yml` now implements that
boundary. Receipt directories live under `/ssd-data/infra/provisioner/releases`.
Rollback also requires the currently observed image to match this attempted
release, avoiding a rollback after a preflight failure or already-reverted spec.
Two regression contracts pass after first failing against the initial draft;
Ansible lint passes its production profile. The playbook has not been run live.
CI pipeline 36/job 74 remains the authoritative image-publication gate; do not
substitute the locally built test image for its output.

Post-release acceptance must not create application data: inside the provisioner
container, acquire the same canonical operation lock and POST an unsupported
engine with the existing token. Expect 409 while locked and 422 after release.
An unauthenticated request must remain 401. The deliberately unsupported engine
cannot reach either native adapter even if the lock regresses. This probe proves
live HTTP/lock behavior only; existing DB creation/idempotence acceptance remains
a separate gate. Never print the token or arbitrary HTTP error bodies.

The opt-in probe is `backup/tests/native-provisioner-lock.py`. An isolated
image fixture starts the baked server with temporary JSON catalog/policy files
and a dummy token, using `--network none` and no Docker socket. The real HTTP
responses were 401, 409, 422, and the fixture exited 0. This verifies the probe
and image behavior locally; production acceptance has not yet run.
