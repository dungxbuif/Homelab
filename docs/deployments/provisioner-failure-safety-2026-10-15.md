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

## Password acceptance gate

Replace the PostgreSQL socket-only smoke with a bounded TCP connection to
its own container hostname on port 5432. Pass credentials only through stdin to a
0600 temporary PGPASSFILE, remove it with a shell trap, disable password prompts
and inherited PGPASSWORD/service overrides. Require SELECT 1 with the generated
password, then require an explicit password-authentication failure with a
different password. A successful wrong-password connection indicates trust or
another password bypass and must fail provisioning before catalog enrollment.
Connection loss alone is not proof of password enforcement. Unit tests cover
all three outcomes and secret handling; native acceptance follows on an isolated
disposable PostgreSQL fixture, without modifying the production HBA policy.

Native SCRAM and trust fixtures both passed and were removed. Subsequent
read-only inspection of production `pg_hba_file_rules` found loopback TCP also
uses trust; non-loopback host connections use SCRAM. Therefore the final gate
uses `hostname` resolution inside the DB container rather than loopback or a
hardcoded IP. Re-run native fixtures for this final form before deploying.
Production HBA is unchanged. Separately, PostgreSQL reports collation version
2.41 at database creation versus runtime 2.36. Investigate affected indexes and
the supported image/library baseline before any REINDEX or REFRESH operation;
no automatic collation mutation is authorized by this smoke-test change.

The hostname variant cannot run with Docker `network=none` because that mode
does not provide the container's ordinary hostname/IP mapping. The failed
fixture was removed. Use a dedicated internal bridge per fixture (no external
egress or host port), then remove that network along with the container. This
preserves isolation while exercising the same hostname-based TCP path.

CI follow-up: pipeline 19 Node validation job 26 was rejected by the restricted
runner's image allowlist before tests ran. Keep the allowlist unchanged; execute
the version-pinned Node test container inside the existing rootless DinD job,
matching the other validation tools. The source bind mount remains read-only.

Final hostname-based native acceptance passed both SCRAM and trust cases on Pi:
7 Ansible tasks OK, 0 failed. Independent Docker label queries found no fixture
containers or networks afterward. Correct-password acceptance and explicit
wrong-password rejection were exercised, and credential-file cleanup passed.
The production hostname path also rejected a deliberately invalid password with
`password authentication failed`; the expected nonzero exit is evidence of the
negative control, not a production outage. The final unit suite has 33 passes.
The final module was deployed through the checksum-guarded repair playbook:
7 OK, 2 changed, 0 failed, including provisioner restart and HTTP health check.
No production database, role, secret or HBA entry was changed by this rollout.
