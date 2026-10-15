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
recorded remote retrieval job remains unfinished and must not be restarted.

Operator command after successful download admission:

```sh
python3 backup/scripts/verify-database-payload.py \
  --run-dir /home/dungxbuif/.homelab-restore-rehearsals/databases-20261015-023158-remote/backup-run \
  --expected-run databases-20261015-023158
```

Run as the owner allowed to read the restored files (restored files may retain
root ownership); do not relax file permissions to accommodate verification.
