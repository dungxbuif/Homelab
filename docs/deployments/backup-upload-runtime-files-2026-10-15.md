# Keep uploader runtime files out of backup payloads

The uploader writes `restic-backup.json` inside the directory it asks Restic to
archive. It also writes preflight/check logs and remote receipts there. These
are operational files, not native database/object/GitLab exports. The active
run reported bytes_done above its initial total; self-inclusion can contribute
to changing input size, but this alone does not establish the full cause of its
ETA estimate or prove any payload corruption.

For subsequent uploads, exclude only these exact root paths inside the mounted
source: `/backup-run/restic-backup.json`, `/backup-run/restic-preflight.log`,
`/backup-run/restic-check.log`, and `/backup-run/remote`. Do not use broad
basename exclusions that could discard same-named RustFS objects in nested
payload directories. Keep logs/receipts locally for diagnosis; no local cleanup,
retention or old-snapshot deletion is part of this change.

The uploader and its shell test already have historical uncommitted preflight,
quota and stale-lock handling changes. Preserve and review those changes; do
not reset them. Verify the live uploader hash against the pre-edit local file
before reconciling the combined source. Pre-edit local SHA-256:
`36e72eaf50d1d9207c4e8a7c1185e4df15dc22d1c343f836f43da21483b9fb99`.

Live Pi hash is different:
`f9cb7fcdb423f67171576ecc5e2db5acc1a75e275b0b08360830d3f8fad21cde`.
Inspection confirms live preflight handling matches the local quota/init/lock
logic, but the live post-check fails directly instead of the local one-time
native stale-unlock/recheck branch. Do not call that local branch deployed.
The new exclusions do not exist in either pre-edit version. Preserve the live
version as the rollback baseline before any later coordinated installation.

Test the exact backup arguments, immutable engine manifest, checksum validation,
receipt separation and existing error-handling contracts. Native Restic matching
uses full paths, per [official exclusion documentation](https://restic.readthedocs.io/en/stable/040_backup.html).
Do not modify or restart the currently active backup or deploy this source while
its backup lock is held. Public application docs are unaffected.

## Verification and source reconciliation

The missing-exclusion regression failed before the four flags were added, then
passed. An opt-in native test created an isolated local Restic repository with
the pinned image, backed up a fixture, listed the actual snapshot, and dumped
one kept artifact. Exact root runtime files were absent; nested same-name files,
the manifest, COMPLETE and native-payload fixture remained. No Drive or real
database was used by that test. Run with
`RUN_RESTIC_INTEGRATION=1 python3 backup/tests/test_upload_exclusions_native.py`.

The shell regression now also checks active-process refusal, failed unlock,
failed recheck, no success receipts on failure, and a single unlock attempt.
All passed, along with the existing Restic contract. ShellCheck's configured
error-severity gate passed; existing SC1091/SC2155 diagnostics remain outside
that gate and are not claimed fixed.

Publishing the uploader alone would omit its working-tree library dependencies.
Reconcile the already present `restic-lib.sh` changes in the same source commit:
digest pin, Docker-visible private rclone working directory, paced Drive calls,
and bounded operation timeout. Preserve these reviewed changes rather than
reverting them or claiming the old committed library provides those contracts.
This is source reconciliation only, not a live Pi/VM deployment. Keep unrelated
historical worktree changes out of this commit.

## Credential working-directory safety gate

Review found the predictable fallback `/tmp/homelab-backup-runtime/rclone`
could be pre-created by another user. `mkdir -p` and `chmod` do not establish
ownership. Before copying OAuth configuration, walk directory components with
no-follow directory descriptors, reject foreign ownership and writable ancestors
(except root-owned sticky temporary roots), and require a private owned final
directory. Use an atomic random directory directly under the system temporary
root when no Docker-visible staging root is configured. Do not repair ownership
or permissions on an untrusted existing directory.

Validate inherited working directories too. Copy only into an exclusive private
file and atomically replace the working config; never follow an existing
`rclone.conf` symlink. Preserve the original credential file. Test foreign-owned
roots, symlinked paths, unsafe modes, safe reuse and cleanup with dummy tokens.
This is a source-only fix while the current backup holds its lock. The separate
container-timeout cleanup finding must also pass before this bundle is deployed.

Implemented `prepare_rclone_workdir.py` and connected it to library initialization
for both new and inherited work directories. Fixture tests include a genuinely
foreign-owned directory while running as root in the local EE, and verify that
the helper refuses it without chmod/chown or copying dummy credentials. Safe
copy, unsafe-mode refusal, no-follow replacement and cleanup are covered.
Independent read-only review found no new blocker in this P1 fix. Shell upload
manifest and Restic contract tests passed. The native snapshot exclusion test
remains opt-in; no remote data or running backup was modified by these tests.

Deployment must include the new helper alongside `restic-lib.sh`; copying the
library alone is invalid. Do not publish this combined uploader/library bundle
as production-ready until timeout cleanup is implemented and verified too.

## Bounded Restic container lifecycle

Replace a timeout around only the Docker CLI with a Python supervisor. Every
call receives a random container name and invocation label. Keep stdout/stderr
streaming unchanged for Restic JSON and logs. On deadline or interruption,
terminate the CLI process group, escalate to KILL after a bounded grace period,
then query only that invocation label, remove only returned full container IDs,
and verify that selection is empty. Each cleanup Docker call has its own bound.
If the daemon cannot confirm cleanup, fail explicitly rather than reporting
success. Do not prune, unlock repositories, or restart a timed-out operation.

Test real TERM-resistant subprocesses and simulated disconnected clients,
cleanup failures, preserved output/exit status and label-scoped removal. Then
exercise a disposable local Docker container with no credentials or data.
SIGKILL/host failure cannot run cleanup; orphan reconciliation after a host
failure remains a separate operational concern, not a guarantee of this helper.

Creation and start are separate. A successful create must return a full container
ID before start; interruption is deferred until the subprocess handle exists.
Unacknowledged creation always returns 125 with the invocation identifier, even
if an immediate label lookup is empty: the daemon might still finish creating
it later. Such an outcome needs operator reconciliation, not a success claim.
Cleanup lookup/removal is bounded and restricted to the invocation and, when
available, the acknowledged ID. No repository unlock occurs in the supervisor.

Verification: six lifecycle tests passed, including TERM-resistant subprocess,
late create after an empty lookup, cancellation during launch, preserved JSON,
nonzero exit and cleanup failure. The full backup Python suite passed 82 tests
with one opt-in skip; the native exclusion test was then enabled separately and
passed. Upload-manifest and error-severity ShellCheck gates passed. A disposable
real Docker container ignoring SIGTERM returned timeout 124 and left no labelled
container; a normal real container retained its JSON stdout and returned zero.
The pinned Restic image also ran `version` through the supervisor successfully.
Review found the two launch races addressed, with no new scoped blocker.

The reconciled uploader explicitly short-circuits after a failed native unlock;
it must not run a subsequent check and mask that failure. All these changes are
source-only until the active backup finishes and coordinated installation saves
the live rollback versions. Install both new Python helpers with the library.
