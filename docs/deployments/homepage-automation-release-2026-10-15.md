# Homepage automation release foundation

## Scope and decision

Start application delivery with Homepage, preserving live content and its
edge-http-net attachment. Do not use the old stack catalog's homelab-net entry
or deploy local image references as though they were published release images.
Production rollout requires a separate restricted Semaphore release action,
previous service-spec receipt, post-check and rollback. No live service was
changed during source/CI adoption.

The local app is `/Users/dungxbuif/workspace/homepage`. Its uncommitted legacy
single-production CI was preserved in local commit b40e428. The old main remains
at archive/pre-automation-main, and codex/automation-delivery preserves migration
work. Current main tracks a clean private GitLab history to avoid publishing old
CI credential history. No force-push or deletion of local history was used.

## Verified publication

- Project 5: `dungxbuif/homepage`, private. Initial clean commit:
  `01299fe7da4bb18aa3350b2fe39769da1bfea69e`, exported from reviewed source d80d43e.
- Runner 1 remains locked with exact project allow-list [2, 5]. No Docker socket,
  allowed-image, privilege or resource-boundary setting changed.
- Pipeline 39/job 83 succeeded. AMD64 image built, isolated HTTP output matched
  source byte-for-byte, nginx -t passed, then the image was pushed.
- Candidate:
  `registry-gitlab.dungxbuif.com/dungxbuif/homepage@sha256:c128afca4e026cfc4f33d4cf1c77adc8cb08f01215a3f2bde76a1ecca12b79fd`.
- Source index was compared directly with VM100 live source: no differences.
  The only reconciliation was the existing Stirling PDF shortcut missing locally.
- Three regression tests, source credential-pattern scan and YAML parse passed.
  Local ARM64 build and isolated HTTP smoke also passed. CI uses rootless DinD
  and the existing approved Docker job image; it performs no SSH or deployment.

The nginx base changed from a floating tag to a pinned observed 1.31.6 OCI index;
the redundant Node copy-only stage was removed. No JavaScript compilation or
application build mechanism was introduced. Production still runs its previous
image; release through Semaphore and recovery acceptance remain unfinished.
The app README describes the new delivery boundary; no public UI behavior changed.

## Restricted release design

Implement a root-owned, fixed-service helper on the Swarm manager. It accepts
only a SHA256 digest matching a root-managed approval record for project 5,
plus the expected current image, separate previous/new content hashes, commit and successful CI
job. A separate forced-command key may invoke only this helper; never widen the
read-only observer identity. The approval file is a bootstrap approval boundary,
not yet a general Git-to-approval automation mechanism.

Use the Docker Engine's versioned service-update API with compare-and-swap
version indexes. Copy the entire current service Spec and change only Image.
Require one replica, VM100 placement, no published ports and the observed edge
network. Hold a persistent exclusive local operation lock. Save the previous
spec in a private durable receipt before mutation. Poll bounded task convergence
and check HTTPS content against the approved source hash. On failure, roll back
only if the current Spec still equals this helper's submitted Spec; use another
versioned update, never an unconditional rollback over someone else's edit.
Report failed, rolled-back and rollback-conflict states separately, always
nonzero for a failed release. A no-op still requires health/content checks.

Before enrollment: unit-test rejection before mutation, successful/no-op release,
private receipts, failed-health rollback and concurrent-edit preservation. Keep
production unchanged until the helper and forced-command boundary pass review.
Registry credentials stay local to the manager, scoped read_registry for project
5; no credential or full service spec is printed to Semaphore logs.

### Verification gate

Run `python3 automation/tests/test_homepage_release.py` in the automation EE
validation job as well as locally. Baseline checks use the previous content
hash; forward checks use the candidate hash; rollback checks return to the
previous hash. This permits actual content upgrades, not only image rebuilds.
The helper is still uninstalled and requires a fresh review before enrollment.
These are internal operational changes; no public Homepage behavior or public
API documentation changes are required.

### Review corrections before authority grant

Fresh review found three deployment blockers: a rejected update could claim
another writer's identical spec, readiness ignored draining old tasks/paused
updates, and file fsync alone did not persist receipt directory entries.
Require explicit update acknowledgement before automatic rollback. A definitive
API rejection returns `update_rejected` without rollback; an ambiguous update
transport failure returns `recovery_required` without further mutations.
Check all service tasks and completed rollout state, and fsync the receipt
directory and its parent before updating Docker. Add regression tests for each
failure before installation. No live deployment is authorized by test success
alone; forced-command enrollment and end-to-end acceptance remain gates.

Verification on 2026-10-15: all 17 release tests pass in
`homelab-automation-ee:local`; CI YAML parses and diff whitespace checks pass.
The fresh reviewer rechecked the fixes and found no remaining helper-code
blockers. The policy suite (4 tests), host observer suite (5 tests), and runtime
policy validator also pass. This is not production release acceptance: helper
installation, restricted identity, UI template, live release/no-op/rollback,
and deployment notification are still pending. Production image is unchanged.

### Restricted enrollment contract

Use a new `homelab-homepage-release` system account on Pi5, with locked password,
no supplemental groups, and root-managed home/authorized_keys. A root-owned
isolated Python forced-command guard accepts only `homepage-release sha256:`
followed by 64 lowercase hex characters, with no additional arguments or shell.
It invokes `/usr/bin/sudo.ws` with a clean environment as Docker owner dungxbuif.
Sudoers permits exactly the helper path and the currently approved digest, not
a wildcard, shell, Docker CLI or arbitrary Python interpreter. Authorization of
a later digest requires refreshing the root approval and exact sudo rule.

The enrollment playbook is Pi5-only and requires an explicit approval flag,
validated public key, approved record, and a project-5 read_registry credential.
Credential/state directories are private to dungxbuif; executable code and the
approval record remain root-owned outside them. Install the authorized key last.
Tests must reject command injection/extra arguments and verify clean exec argv,
fixed identity, exact sudo rule and no secret values in task output.

### Enrollment acceptance, 2026-10-15

- Installed on Pi5 through `homepage-release-enroll.yml`: 10 tasks, 8 changed,
  zero failures. Repeated enrollment: 10 tasks, zero changed, zero failures.
- Fresh boundary review found the sudoers digest colon must be escaped. Fixed
  to `sha256\:` in sudoers only; target `/usr/sbin/visudo` validation passed.
- Three guard tests and four enrollment contract tests pass; ansible-lint passes.
- Actual restricted SSH: `id` and shell-suffixed commands return exit 2. A
  syntactically valid but unapproved digest is rejected by sudo (exit 1).
  These tests performed no Docker mutation.
- Project 5 deploy token ID 3 has only `read_registry`, expires 2027-01-13.
  It is stored in ignored 0600 local credentials and private manager state;
  never in Git, the Semaphore runner, or task logs. Rotation must precede expiry.
- Approval commit/job were checked against GitLab job 83 and its digest artifact.
  Live HTTPS output matches that exact commit's `index.html` byte-for-byte.

This supersedes the earlier uninstalled status. The helper and restricted key
are now installed, but **no Homepage release has run**. The production image
remains `homelab/homepage:vm100-20261007-stirling`. Semaphore template creation,
live release/no-op/recovery acceptance, and notifications are still pending.

### Semaphore release entry point

Add one manual template, `Release approved Homepage`, using a dedicated key and
inventory for `homelab-homepage-release@10.10.0.5`. No become key, registry token,
Docker socket or general SSH identity enters the runner. Pin SSH host identity
with the existing known_hosts and select the release public key explicitly.
The playbook accepts a digest, validates it before constructing the fixed raw
command, and treats only `success`/`unchanged` with matching image evidence as
success. Any rollback or ambiguous result fails the task visibly.

Bootstrap defaults to dry-run, rejects duplicates/drift, and refuses enrollment
if project users extend beyond owners. Current project 1 membership was checked:
only admin (owner). This is not a completed multi-role policy: adding Task Runner
users requires a separate release-project/template authorization design first.
No schedule or automatic deployment is created. Unit-test bootstrap dry-run,
idempotence, drift, duplicate resources and non-owner rejection before applying.

Created and independently read back on 2026-10-15: template 6, inventory 5,
key 6. Bootstrap rerun reuses these exact resources. Seven bootstrap tests pass,
including environment-reference drift and unexpected schedule rejection added
after review. Playbook ansible-lint passes. No release task has run yet.

Operator entry point:
`https://semaphore.dungxbuif.com/project/1/templates/6`.
As admin, open **Release approved Homepage**, select **Run**, and inspect its
task output for the receipt summary. The playbook default is the already
approved candidate digest; no registry credential entry is needed. Do not add
a schedule or use this template for another app. To authorize a different
release, first verify its CI evidence and update the root approval/exact sudo
rule through the enrollment workflow. A failed/rolled-back task is not success;
inspect the manager's private receipt before retrying an ambiguous result.

Negative runner acceptance: task 25, template 6, runner 1 checked out
`dfc0aaf5f858c92398bdc975723b0b21496a21e5`. An intentionally invalid digest failed
the first assertion with changed=0, before the raw SSH command. Task status is
`error` as expected for this negative test, not a failed production rollout.
No positive release task has run. CI pipeline 43 validates this integration
commit; inspect its current status before the first real release.

## Production release acceptance

Pipelines 41-43 completed successfully. Task 28 on runner 1 checked out dfc0aaf5
and released the approved candidate successfully: six tasks, changed=1,
failed=0. Receipt `homepage-release-tr02tjtu` on Pi records the prior service
spec and approval; candidate app commit remains 01299fe7/job 83. The helper
reported success at 2026-10-15T00:36:54Z. An independent HTTPS fetch returned
200 with approved content SHA256
`f121c1b37ce0174e1e995293be4a579673e95d07fe7636b658304536c81be4bc`.
Task 29 is the same-digest no-op acceptance and must be checked to completion.

Reconcile the old stack catalog: its homelab-net network, local image digest and
claimed resource limits were stale. Record edge-http-net and the published
registry digest. Keep observed resource limits empty and the proposed 0.5 CPU /
512 MiB separately; this release intentionally did not apply resource changes.
The generic deploy contract checker must reject a digest different from the
catalog's approved digest, not merely check that the input looks like SHA256.
This does not replace the root-managed approval or grant arbitrary deployment.
Add positive/negative contract tests before changing the checker.

Task 29 completed successfully with status `unchanged`, six tasks and changed=0;
receipt `homepage-release-o1s5ryzr`. Live rollback rehearsal and Mezon deployment
notification are still outstanding; do not count deploy + no-op as two complete
Git-to-notification acceptances.

Before rollback rehearsal, scope registry auth to the approved Homepage registry
repository. A rollback to the legacy local image must explicitly send empty auth,
not reuse the new registry credential. Docker's service-update API inherits auth
from the current spec when the header is omitted, so omission is insufficient:
https://docs.docker.com/reference/api/engine/version/v1.51/ . Add transport-level
tests for both scoped auth and explicit empty rollback auth, then update the
installed helper without restarting or changing the running service.

The scoped-auth fix passed all 18 helper tests in the automation EE and fresh
review found no blocker. Two deploy-catalog tests and ShellCheck also passed.
This improves the rollback boundary but is not a substitute for a live recovery
rehearsal. No public UI/API changed; internal operational docs are the affected
documentation surface.

## Installed helper revalidation

Read-only SHA256 comparison on 2026-10-15 confirms the installed Pi helper and
reviewed source both equal
`931fe0e5c2d9758b0a8ba40cb2602e8e7e062e08eeac817af029db954ddd99ae`.
The scoped registry-auth correction is installed; no reinstall or production
restart was needed. All 18 helper tests passed again. Semaphore bootstrap
dry-run returned existing key6/inventory5/template6. Live rollback and
notification acceptance remain outstanding; matching helper hashes and an
idempotent bootstrap do not prove either acceptance.
