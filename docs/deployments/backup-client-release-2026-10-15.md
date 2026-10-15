# Controlled backup client release

Deploy the reviewed OAuth-directory, container-lifecycle and upload-exclusion
changes through Ansible on Pi5 and VM100. This is not a scheduler, credential,
catalog, retention-policy or database change. Public app documentation is
unaffected; this Markdown is the internal operator/agent record.

## Restore verifier follow-up, 2026-10-15

The remote PostgreSQL rehearsal exposed one deployment gap: the source
`backup/scripts/verify-database-payload.py` verifier was not included in the
four-file runtime client bundle on Pi5/VM100. The targeted rehearsal therefore
used an equivalent read-only one-off check for its selected artifact set. Add
the verifier to the same lock-aware release bundle and require its exact source
checksum in release tests. This changes no scheduler, backup payload, or
credential behavior; it makes the documented full-payload verification command
available on both backup hosts.

The Pi5 release template uses a dedicated SSH key enrolled only for the
`dungxbuif` account. The password bootstrap key is not used by the job, and no
VM100 write credential is enrolled by this follow-up.

The deployment helper must hold the same existing exclusive flock as backups
for the entire installation. Pi5 uses
`/ssd-data/infra/backups/homelab/.homelab-backup.lock`; VM100 uses
`/run/lock/homelab-backup.lock` (verified from selected nonsecret runner settings).
Never unlink or recreate a lock. If busy, return without changing live files;
do not stop any job to obtain it.

Ansible stages a fixed five-file allowlist and its SHA-256 manifest privately.
Under the lock, validate all bytes and existing targets, preserve original bytes
and permissions in a private durable receipt, install helpers before the library
and uploader, and verify installed hashes. Do not copy the whole repository or
overwrite inventory/secrets. Use atomic replacement per file; the group is
serialized, not filesystem-transactional. Compatible helper-first ordering also
avoids a library referencing an absent helper after an unexpected host failure.

On an ordinary installation error, restore changed targets only while their
content still matches this release. Preserve a concurrent external edit and
report a rollback conflict instead of overwriting it. Keep receipt metadata for
manual recovery after host failure or SIGKILL; do not claim automatic crash
recovery. A byte-identical repeat must be a no-op.

Verify busy-lock refusal, corrupt payload refusal, target-symlink refusal,
successful installation, no-op replay and rollback with temporary fixtures.
Run Ansible lint and check mode before applying after backup completes. Then
verify live hashes and a bounded non-upload command; the next actual backup
and full remote restore remain separate acceptance gates.

## Live release acceptance, 2026-10-15

Semaphore template 7, `Release backup client (Pi5)`, is now the enrolled
operator path for this change. It uses the dedicated Pi5 SSH key and inventory
only; no VM100 write credential was added. Live task 65 completed successfully
after the path-resolution correction for the imported playbook. Its receipt
reports the five staged files and the Pi5 lock-aware release changed only the
three files whose source bytes differed:

- `prepare_rclone_workdir.py`
- `restic-lib.sh`
- `verify-database-payload.py`

The canonical verifier is installed on Pi5 at
`/ssd-data/infra/backup-runner/app/backup/scripts/verify-database-payload.py`
with the expected non-secret ownership and mode. A full local source-run
verification passed on Pi5 for run `databases-20261015-023158`:

```json
{"artifacts_verified":29,"bytes_verified":6915289967,"run_id":"databases-20261015-023158","scope":"database_payload_integrity_only","status":"verified"}
```

The five live Pi5 client hashes were compared against the checked-out release
source after task 65 and matched byte-for-byte. This closes the deployment
integrity check for Pi5; it does not enroll a write path for VM100.

The follow-up live task 66 ran commit `bb2c924` through the same template and
completed successfully. The release helper returned `changed=false` with an
empty file-change list, proving the published client is idempotent. The
playbook produced the controller-side `artifacts/backup-client-release.json`
post-check artifact; the recap was `unreachable=0` and `failed=0`.

The selected remote PostgreSQL rehearsal also passed: four restored payload
artifacts, 98,988 bytes, native import in a disposable network-isolated
PostgreSQL 16 container, `SELECT 1`, 30 user tables and seven expected roles;
the disposable container was removed. This is targeted PostgreSQL evidence,
not acceptance of a full all-database/CouchDB/GitLab/RustFS Drive restore.

## Implementation verification

The helper and `automation/ansible/playbooks/backup-client-release.yml` implement
the fixed bundle. Nine local release tests passed, including real lock contention,
rollback conflict preservation and directory-fsync ordering. The full backup
suite inside the Linux EE passed 91 tests with one native opt-in skip. Ansible
lint passed its production profile; environment cache/deprecation warnings are
not treated as rule failures. Independent review's directory-durability finding
was fixed and re-reviewed before attempting live check mode.

Pi5 `--check` passed for the initial four-file release: live files were not replaced.
Check mode deliberately creates and removes a private staging candidate while
validating bytes and acquiring the real lock; its Ansible changed count therefore
is not evidence of a live deployment. The helper's `check_mode=true` result is
the authoritative distinction. VM100 uses privilege escalation only for the
lock-aware helper because its production lock is root-owned.

The preceding backup completed naturally: systemd inactive, MainPID=0,
Result=success, ExecMainStatus=0. Pi success marker and remote receipt agree on
run `databases-20261015-023158`, snapshot
`28872481b537f9666a30cbca00b8f137fe886deff549d4f7c8bb135a23c093c3`.
This proves that run's post-check, not the new source rollout or a restore test.

## Runtime-directory compatibility correction

The initial four-file install completed on both hosts, but the first Pi version smoke
correctly refused group-writable staging ancestors (mode 0775). VM's old runtime
path is under ubuntu-owned `/opt/apps`, also inappropriate for root OAuth work.
Do not weaken the no-follow/ownership checks or chmod broad application trees.
Move only temporary OAuth working copies to Docker-visible private paths:
Pi5 `/home/dungxbuif/.homelab-backup-runtime` owned by dungxbuif, and VM100
`/home/ubuntu/.homelab-backup-runtime` owned by ubuntu, both mode 0700.
Preserve source credentials and update only `RCLONE_CONFIG_WORK_ROOT` in each
private runner env. Pin the same VM path in the systemd drop-in, then reload
definitions without restarting any job. VM has ProtectSystem=full, not strict;
the service-owned home path also passes the helper's ancestor ownership check
and is visible to Docker without weakening that setting.

Use `backup-runtime-config.yml` with explicit approval and per-file rollback
copies. Repeat version smoke through the full installed library on both hosts
and verify temporary configs/container cleanup. Release receipts for the first
installation are Pi `backup-client-xhk3u6rk` and VM `backup-client-qp175jxt`.
Installation alone was not sufficient; runtime smoke remains required.

### Installed result

Both hosts completed the lock-aware install (initial four files, no job restart) and
the runtime-path correction. VM systemd definitions were reloaded only.
The full installed library successfully ran pinned Restic 0.19.1 `version`
on Pi arm64 and VM amd64 using each host's real environment and private config
working copy. This command does not upload or verify remote repository data.
The source OAuth credential was not rotated or moved.

The first live VM100 `database-instances` upload after the runtime-path
correction completed successfully: run
`database-instances-20261015-112854`, snapshot
`fa3aa6c6606183910918917784e12546e08f77668ccb8efd58cc791dfbd42943`, and
Restic integrity check passed. The separate Pi5 restore rehearsal was not an
acceptance result: it stalled before producing a payload and was stopped after
its exact process tree held the global lock for more than three hours. It must
be rerun with a bounded, observable restore check.

Post-install verification for the initial release required all four live SHA-256 hashes
to match the reviewed source, mode-0700 empty runtime directory after smoke,
and zero remaining invocation-labelled containers. Preserve both release
receipts and environment rollback copies. The next full upload and the planned
Google Drive restore rehearsal remain required; do not infer them from version
smoke or from the successful backup that preceded this deployment.

## Source CI confirmation

After the live Pi5 client release, the source branch passed GitLab pipeline 166
at commit `bc8eacebac2389db9e3d66cec49c13148410c4ae`. This includes the
candidate-generation enrollment tests, scheduler contract, backup contracts,
and the OpenTofu/Proxmox static validation suite. The published automation
execution environment is digest-pinned in the automation image security
runbook; this CI result does not by itself perform a VM100 or Pi5 rollout.
