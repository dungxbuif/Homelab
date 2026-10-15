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
