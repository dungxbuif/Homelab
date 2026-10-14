# Provisioner failure safety before remote acceptance

## Decision

Before creating disposable resources through the new remote executor, fix two
pre-existing unsafe failure paths in the private provisioning backend:

- Reject catalog ownership/policy/secret conflicts before native mutations.
  Reuse the catalog registration validator without writing the catalog.
- Never delete a newly generated secret after a native operation starts: SQL
  and CouchDB calls may have partially committed even when the caller receives
  an error. Preserve credentials for explicit reconciliation; do not roll back
  or rotate application credentials automatically.

Tests must prove catalog conflicts invoke no Docker/native operations and a
post-create failure retains the secret for both engines. Deploy only the
changed Python module after comparing its live checksum, restart only the
private provisioner to reload imports, then check health. Catalog and database
contents are not changed by deployment. PostgreSQL authenticated smoke currently
uses a local socket and needs a separate TCP/password acceptance check before
claiming end-to-end authentication. No public API shape change is intended.

## Verification and rollout

All three new regressions failed against the old code for the intended reasons.
After the fix, 30 Python backup tests passed. The live module matched the old
reviewed SHA256 `9249a252fb5f3bf109cdf051877fab499a0c06a4d85a98790498eefce39b8a95`
before deployment. All nine Semaphore tasks were terminal. The repair playbook
saved a rollback copy, replaced only this module, restarted the provisioner and
verified private HTTP health: 7 OK, 2 changed, 0 failed. No database or secret
was created by this repair.

The initial installer lint reported a handler-style violation; the restart was
subsequently converted to a notified handler with explicit flush before health
verification. Revised lint passed the production profile; a second live run
completed with 6 OK, 0 changed, 0 failed, confirming idempotence and health.

## Operator recovery behavior

A provisioning failure can leave partially created resources. The generated
Swarm secret now remains available instead of being deleted. Treat the task as
failed, inspect the matching role/database/security and catalog, and reconcile
before retrying. Do not delete that secret or reset the user's password blindly.
This is not a transactional rollback implementation. Conflicting catalog
metadata is rejected before native mutations; simultaneous provisioning still
needs a whole-operation concurrency guard before broad multi-operator rollout.
