# Database remote recovery acceptance

This extends the approved control-plane backup acceptance. Local native restores
already passed for RelayHub's newly enrolled PostgreSQL instance, but do not
prove recovery from Google Drive. Source run: `databases-20261015-023158`.

## Gates and procedure

1. Wait for the existing VM100 `homelab-backup@databases.service` (PID 1659814)
   to finish naturally. Require a successful terminal result and the Pi success
   marker to name this exact run. Do not restart or overlap the upload.
2. Read its exact 64-hex remote snapshot ID from the success marker and completed
   run; require them to agree. Reject stale markers and empty/ambiguous IDs.
3. Confirm free space for the full exported payload, a disposable restore and
   existing backup retention. The current manifest is about 6.9 GB of payload.
4. Under the existing Pi backup flock, use installed `restore-staging.sh` and
   existing private runner environment to retrieve that snapshot into a NEW
   private directory. Never restore into a production data mount, the original
   run, or an already existing directory. Record the exact operation handle;
   observation timeout alone never authorizes a second retrieval.
5. Verify retrieved manifest/run identity, COMPLETE and all checksums. Verify
   the manifest contains `relayhub-dedicated` with both databases and globals.
   Reports belong outside the retrieved payload, never in the source upload.
6. Restore retrieved RelayHub globals and both custom dumps into a uniquely
   named disposable PostgreSQL container using the exact already installed
   matching image. Use network=none, no published ports or production mounts,
   tmpfs data, bounded CPU/memory, and native error-stop commands. Check table
   counts (relayhub 14; postgres 0) and record failures without leaking hashes
   of role passwords or SQL contents. Remove only the captured test container ID.
7. Preserve a secret-free verification result and exact snapshot ID. A successful
   RelayHub rehearsal proves only this instance's remote native recovery, not
   all shared PostgreSQL/CouchDB databases or application-level behavior. Those
   restore acceptance items and GitLab/RustFS rehearsals remain separate.

Do not prune/delete an original backup, change Drive OAuth configuration or
send a success notification before these checks finish. Remote retrieval reads
the same `homelab-backup-488616` OAuth-backed repository; it does not switch
projects. The success of a sampled Restic check alone is not a restore test.

Public application docs are unaffected. This internal Markdown is the
operator/agent-readable execution record; append actual evidence after running.

## Download admission, 2026-10-15

The source job is terminal success (MainPID=0, inactive, Result=success,
ExecMainStatus=0). Its success marker and run receipt agree on exact snapshot
`28872481b537f9666a30cbca00b8f137fe886deff549d4f7c8bb135a23c093c3`.
Pi free space before retrieval is 306,330,124,288 bytes. The new backup client
and private OAuth runtime roots were installed and version-smoked on both hosts.

Use Ansible asynchronous command execution with a five-hour outer budget; the
installed Restic supervisor retains its four-hour operation deadline and bounded
cleanup. The command takes the existing Pi backup flock without replacing its
inode and revalidates marker/receipt inside that lock before retrieval.
Destination is a new mode-0700 directory:
`/home/dungxbuif/.homelab-restore-rehearsals/databases-20261015-023158-remote`.
Its private parent is outside the group-writable staging ancestry. Log and PID
receipts live beside, not inside, the restore target. Preserve an incomplete
destination on failure; never silently retry into or delete it. Record the
returned async job ID and poll that same operation until terminal.

Started async job `j186891193321.3128007`; its result file is
`/home/dungxbuif/.ansible_async/j186891193321.3128007`.
First poll reported started=true, finished=false, and the private PID receipt
matched live bash PID `3128034`. No terminal download/restore success is claimed.

## Payload verification implementation

Add a read-only `verify-database-payload.py` gate before native restore. Require
the exact expected run ID, complete database manifest, matching COMPLETE marker,
nonempty unique safe artifact paths, and agreement between manifest hashes and
the checksum index. Stream SHA256 over every declared artifact, reject symlinks
and traversal, and return only counts/bytes/run identity. This verifies retrieved
payload integrity, not remote provenance by itself, DB recoverability or runtime
health. The orchestration must first require the recorded retrieval job's zero
exit status and the exact snapshot admission receipt. Reports stay outside the
retrieved tree. Native PostgreSQL export/restore mechanisms remain unchanged.

Tests cover successful full verification, byte corruption, missing files,
wrong run/marker, duplicate paths, checksum-index mismatch, symlinks and escape.

Verification: six targeted tests passed; full backup Python suite ran 98 tests,
97 passed and one opt-in native integration test skipped. Independent review
found no concrete defect in this scoped verifier. Read-only execution through
Ansible against the existing LOCAL source run verified all 29 declared
artifacts, totaling 6,915,289,967 bytes. This is compatibility/integrity evidence
for the verifier, explicitly not proof of the remote downloaded copy. The
recorded remote retrieval job reached its terminal timeout and must not be
reused.

## Timeout diagnosis and controlled retry

The recorded retrieval job `j186891193321.3128007` reached its terminal result
on 2026-10-15 with `rc=124` after exactly four hours. The Restic log reported
`Restic command deadline exceeded`; the container was then reconciled and
removed. This is a bounded timeout failure, not evidence of an invalid
snapshot: the read-only target had reached about 6.4 GiB, PostgreSQL and most
metadata files were present, and the large CouchDB export was still being
written when the deadline fired. The incomplete target is retained as
evidence and is not reused.

The controlled follow-up uses the same exact snapshot in a new target with an
8-hour `RESTIC_COMMAND_TIMEOUT` and a longer Ansible observation budget. It
must still hold the existing backup lock, use the same project-owned OAuth
repository, and require the terminal zero exit status before verification.
No production mount, database, or backup source is modified by this retry.

An initial retry wrapper `j213008523879.3252966` terminated immediately with
`rc=127` because the Ansible shell defaulted to `/bin/sh` and could not run
`source`; it did not create a restore container or target. The corrected retry
`1` was started only after that wrapper reached terminal state: async job
`j871550432349.3253245`, target
`/home/dungxbuif/.homelab-restore-rehearsals/databases-20261015-023158-remote-retry-1`,
and timeout override `RESTIC_COMMAND_TIMEOUT=8h`. The first poll reported
started=true and finished=false. The original incomplete target and its log
remain untouched for evidence.

Operator command after successful download admission:

```sh
python3 backup/scripts/verify-database-payload.py \
  --run-dir /home/dungxbuif/.homelab-restore-rehearsals/databases-20261015-023158-remote/backup-run \
  --expected-run databases-20261015-023158
```

For retry `1`, substitute:

```sh
python3 backup/scripts/verify-database-payload.py \
  --run-dir /home/dungxbuif/.homelab-restore-rehearsals/databases-20261015-023158-remote-retry-1/backup-run \
  --expected-run databases-20261015-023158
```

Run as the owner allowed to read the restored files (restored files may retain
root ownership); do not relax file permissions to accommodate verification.

At the latest observation the corrected retry container was still running with
the exact snapshot, after roughly 30 minutes. Its network transfer had reached
about 154 MB and the isolated target had not yet materialized payload files;
this is an in-progress remote restore, not a verification result. Keep polling
async job `j871550432349.3253245` and do not start a second retry or run native
database restore until the container exits zero and the payload verifier passes.

## Targeted PostgreSQL rehearsal

The full retry later terminated with `rc=143` after its target remained an
8 KiB private directory; no restore payload was accepted and no process from
that retry remains. Its target and log are retained as failure evidence. A
separate bounded PostgreSQL-only rehearsal was then started from the same
snapshot after the lock became free. It uses a new private target and includes
only the RelayHub PostgreSQL adapter metadata, globals, `postgres.dump`,
`relayhub.dump`, `manifest.json`, `COMPLETE` and the checksum index. The remote
operation is PID `3367943` with log
`/home/dungxbuif/.homelab-restore-rehearsals/databases-20261015-023158-pg-only-1.log`.
The operation exited successfully after restoring 9 entries (7 files/
directories) in 5:44. The selected target is verified below; this result does
not certify the full all-database payload.

## Targeted PostgreSQL rehearsal result

The private target contains the exact run marker, manifest, checksum index,
PostgreSQL adapter metadata, globals, `postgres.dump`, and `relayhub.dump`.
The targeted read-only integrity check verified the run ID and `COMPLETE`
marker, all 3 control files, and all 4 selected PostgreSQL artifacts. The
selected artifact bytes totalled 98,988 bytes and matched the checksum index.

Native restore then ran twice in disposable `pgvector/pg16` containers because
the first run's post-check command had a shell-quoting error after import; its
container was removed by the trap. The corrected run used `network=none`,
tmpfs-only database storage, 1 CPU, 1 GiB memory, and no published ports or
production mounts. It loaded `globals.sql`, restored `relayhub.dump` with
`pg_restore --exit-on-error --no-owner --no-acl`, returned `SELECT 1`, found 30
user tables and 7 expected application roles, and removed the disposable
container.

This is a successful remote PostgreSQL selected-payload recovery acceptance,
not a full all-database/CouchDB/GitLab/RustFS restore. The canonical full
payload verifier is present in source but was not in the old four-file runtime
bundle; its release follow-up is recorded in
[`backup-client-release-2026-10-15.md`](./backup-client-release-2026-10-15.md).

## Retry progress and checksum diagnosis

The retry later materialized all 29 manifest paths and the `COMPLETE` marker,
with about 6.4 GiB visible from inside the restore container. A checksum pass
started while `restic restore` was still active correctly found 7/29 entries
missing or incomplete, including large CouchDB/GitLab payloads and several
PostgreSQL files. This is an in-progress write race, not final corruption
evidence. The temporary checksum container was removed after its output was
captured. The full retry remains historical incomplete evidence; the targeted
PostgreSQL rehearsal above is the only remote recovery acceptance currently
passed.
