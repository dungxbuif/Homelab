# Remote PostgreSQL provisioning acceptance

Use one disposable staging database through live Semaphore template 1. Reserve
an absent fixture name, role and Swarm secret, and record a private receipt
before submitting the task. The helper may verify and remove only those exact
resources and only with that receipt. Never terminate client sessions or use
DROP CASCADE. No production data or schedule changes are required.

Verify the owner and absence of elevated role flags, exact catalog metadata and
selection by the existing backup adapter. Run the native PostgreSQL backup
adapter on a private, in-memory filtered copy of the catalog; validate its custom
dump with pg_restore --list, then remove temporary dumps (including globals).
This proves local backup enrollment/dump, not Google Drive upload or restore.
Run the same Semaphore request again to verify no credential rotation. Remove
the fixture database, role, secret and catalog row afterward, preserving task
history and evidence. If provisioning fails, inspect the failure before retrying
and still clean only resources recorded by the preflight receipt.

The existing collation mismatch may prevent CREATE DATABASE. Do not suppress
that error or refresh collation metadata without the required rebuild analysis.
Only internal operational docs change; no public application interface changes.

Task 10 stopped before database operations because template 1 retained its old
`git_branch=main` override. Repository 2's branch does not override that field.
The runner checked out `bfad089d...`, which lacks the playbook. Correct the
template override to `codex/automation-bootstrap` while preserving its remaining
settings, and make the migration helper set/check this field explicitly.

Tasks 11 and 12 succeeded (create changed=True, repeat changed=False). Independent
verification found the catalog became root:root 0600 after atomic registration,
blocking the unprivileged backup account. Fix registration to preserve existing
file owner/mode across atomic replacement. Restore only this catalog's owner to
the confirmed backup account (UID/GID 1004); retain mode 0600. No broad chmod.
Repeat native dump and cleanup before the next scheduled database backup.

After owner restoration, verification passed: dedicated owner has no superuser,
createdb, createrole, replication or bypass-RLS flags; exact new entry is selected
by the current backup adapter; native pg_dump and pg_restore --list succeed.
Temporary dump directory (including the globals export) was removed. Swarm
secret ID `nnxmuidd2yvcmfht16gpvx01y` and creation timestamp were unchanged by
task 12. Task history is retained, including task 10's source-branch failure.

Registration now opts into preserving metadata in `common.write_json`; other
backup artifact writes keep their existing default 0600 behavior. Regression
testing first reproduced mode loss, then all 33 Python tests passed. Deployment
compared both live source hashes before replacing common.py/register_resource.py
with rollback copies. Native verification writes an isolated user-owned fixture
from inside the root provisioner and requires the result to remain UID/GID 1004
and readable by the backup account. Cleanup needs sudo only to acquire the
root-owned registration lock; it preserves catalog owner/mode and refuses
resources without the preflight receipt or with changed ownership metadata.

Live writer repair and root-to-user ownership check passed: 11 tasks OK, no
failures. Fixture cleanup then passed: database, role, secret and catalog row
are absent; no forced session termination or cascading drop was used. Both
playbooks passed production-profile lint, and 12 Semaphore Node tests pass.
The acceptance establishes remote PostgreSQL provisioning, stable credentials,
catalog enrollment and local native dump/list only. Google Drive publication,
restore rehearsal, CouchDB acceptance and the broader automation plan remain
separate outstanding gates. The collation warning did not prevent this CREATE
DATABASE, but still requires its own integrity assessment.
