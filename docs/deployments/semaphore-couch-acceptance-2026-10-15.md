# Remote CouchDB acceptance

Reserve a new staging database, user and Swarm secret before submitting template
1 through Semaphore. Verify the exact members/security policy, user role, denial
of anonymous access and catalog metadata. Write one disposable document with a
small attachment, then run the deployed CouchDB export adapter against only the
new entry in a private filtered catalog. Inspect the exported document,
attachment and security policy, and delete temporary exports. Repeat provisioning
to check idempotence. Confirm catalog UID/GID/mode remain 1004:1004:0600 after the
root provisioner writes it. This exercises the previous ownership repair through
the actual registration path.

Cleanup requires a prior absence receipt, exact fixture prefix and unchanged
ownership/security metadata. Delete only the fixture database, user document,
secret and catalog entry, with catalog registration locking and metadata
preservation. Keep Semaphore history. This does not demonstrate Drive upload or
disaster restore; those remain separate gates. Internal documentation only.

## Verified result

- Task 13 created the CouchDB staging database/user through VM100 runner 1.
- Independent verification passed exact user role/security, anonymous denial,
  backup catalog selection and catalog ownership/mode 1004:1004:0600.
- The deployed adapter exported one document, its attachment bytes and security
  metadata correctly. Temporary exports were removed.
- Task 14 succeeded with changed=False. Secret ID `27jk8dzsghlhr1ls7yeotd8mf`
  and its creation timestamp were unchanged between the two runs.
- Receipt-gated cleanup passed: database and user return 404; secret and catalog
  row were removed. No unrelated resource was selected for deletion.
- The shared bounded fixture playbook passed production-profile lint; the
  existing Python suite passed 33 tests. No production database was recreated.

GitLab pipeline 21 Node validation job 32 and automation validation job 33 both
succeeded, confirming the restricted-runner CI correction; image-build job 34
was still running at inspection. Pipeline 22 was queued. Neither pipeline is
claimed fully successful from validation alone.

VM100's five backup timers remain active. At 2026-10-15 00:29 +07 the next DB
timer was due at 01:00 +07. This schedule check is not proof of a new remote
snapshot or webhook delivery. Continue remote backup verification separately.
