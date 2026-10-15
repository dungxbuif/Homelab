# Family Tree private database repair

Read-only production probe in task container `d428f5317271` failed with
`ENOTFOUND pgbouncer` for the configured Docker DNS endpoint on port 6432.
The app has only edge-http-net; PgBouncer has proxy_net, homelab-net and data-net.
Thus matching each service's current network policy did not prove dependency
reachability. `/login` alone is not an adequate database acceptance check.

Repair decision: create attachable encrypted overlay `family-data-net`, attach
only PgBouncer and the Family Tree Swarm service, keep edge-http-net and every
existing PgBouncer network. Do not publish ports, change credentials, change
app code/image/mounts, migrate data or restart PgBouncer. Preserve private
service/Compose receipts before mutation. Add the observed existing PgBouncer
networks and new network to its actual Compose source; the source currently
declares only proxy_net and must not drop runtime data-net/homelab-net on a
future recreate. Use structured YAML and syntax-check before replacement.

Verify manager-side network shape, bounded Swarm convergence, then read-only
SELECT 1 from the new VM100 app task and HTTPS `/login`. A rollout error must
not be reported successful. Keep exact prior service spec/source for rollback;
do not blindly restore over concurrent edits. No automatic image/code rollout
is authorized by this repair. Record actual receipts, checks and remaining gaps.

Internal runbook and runtime policies are affected. Public app behavior is a
connectivity repair, with no API/UI contract change, so public docs need no edit.

Pre-apply review requires preserving source UID/GID/mode, capturing PgBouncer's
immutable container ID and rechecking its memberships before source publication.
Persist candidate source/hash and endpoint pre-state before any network/source
mutation. Reject symlink/non-regular source files and concurrent replacement.
Regression tests cover metadata preservation, endpoint replacement, and a
connection failure after source publication; such failure must retain recovery
evidence and must not report a successful rollout.

## Review corrections

Three apply-path regression tests reproduced the review failures before the fix.
The helper now preserves source metadata, checks PgBouncer identity/memberships,
connects immutable endpoint IDs, and saves recovery intent before mutations.
Source opening rejects symlinks; replacement checks original inode and metadata.
The tests are enrolled in the existing CI validation job. These fixture tests
are not production convergence or DB reachability evidence.

A fourth regression reproduced a concurrent source edit during the final Docker
inspection. That inspection now precedes the last source snapshot/check. The
helper lock serializes only this helper: check-plus-rename is not filesystem CAS
against unrelated writers. Run only in an exclusive Compose maintenance window;
do not claim general concurrent-writer protection until all writers share a lock.

## Conditional recovery

Receipts are private because the original service spec and Compose may contain
credentials. Never print or commit them. A failed run requires inspection before
retry; an existing network/source change is not automatically rolled back.

1. Compare the live service Spec to `service-candidate.json`. Only if identical,
   restore the saved `service-before.json` Spec using the CURRENT service version
   as the Docker API CAS guard. A mismatch requires operator reconciliation.
2. Restore Compose only if its SHA256 still equals `compose-candidate.sha256`.
   Validate the saved YAML and atomically restore bytes plus UID/GID/mode from
   `compose-before.metadata.json`. Never overwrite a concurrent edit.
3. Disconnect only the captured PgBouncer ID from the captured dedicated network
   after confirming it was absent in `pgbouncer-before.json` and Family no longer
   uses it. Preserve every pre-existing membership. Do not remove the overlay if
   any other endpoint/service adopted it; leaving an unused network is safer
   than removing a network owned by another rollout.
4. Record failed/rolled-back/conflict explicitly, then test the resulting state.
   Restoring the former topology restores the pre-existing DB outage, not health.

## Applied and verified

Applied through Ansible on 2026-10-15 after confirming VM100-only placement,
one replica, and source owner UID/GID1004 with mode0664. Private receipt:
`/home/dungxbuif/.homelab-network-repairs/family-q6r8e6wb` on Pi5.

New VM100 task container `8fc4e6ec06dc` joined edge-http-net and family-data-net.
Read-only `SELECT 1 AS ok` using the app's installed pg client and actual
DATABASE_URL succeeded through `pgbouncer:6432`. Public HTTPS `/login` returned
200. No application image/code, credentials, or database records were changed.

An initial post-check used pg's `statement_timeout` startup parameter, which
PgBouncer rejected with 08P01. This was a probe incompatibility, not an app
configuration change. The corrected probe uses client-side `query_timeout`
and `connectionTimeoutMillis` (both 5000ms) and succeeds. Do not reintroduce
unsupported startup parameters into operational probes.

Seven regression tests pass. Runtime policy now includes the dedicated network
for Family Tree and PgBouncer. This verifies database connectivity and login
ingress, not every app workflow or S3 operation, and is not the full automation
control-plane acceptance.

Manager verification: Swarm update completed at 05:19:08 UTC; live Spec exactly
matches the saved candidate. PgBouncer retained its original container ID and
2026-10-06 start time. The overlay is encrypted, Compose persists all four
PgBouncer memberships, and source permissions remain0664. The policy regression
fixture was updated from the former edge-only membership to the verified pair.
