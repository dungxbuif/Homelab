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
