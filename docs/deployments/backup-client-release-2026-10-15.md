# Controlled backup client release

Deploy the reviewed OAuth-directory, container-lifecycle and upload-exclusion
changes through Ansible on Pi5 and VM100. This is not a scheduler, credential,
catalog, retention-policy or database change. Public app documentation is
unaffected; this Markdown is the internal operator/agent record.

The deployment helper must hold the same existing exclusive flock as backups
for the entire installation. Pi5 uses
`/ssd-data/infra/backups/homelab/.homelab-backup.lock`; VM100 uses
`/run/lock/homelab-backup.lock` (verified from selected nonsecret runner settings).
Never unlink or recreate a lock. If busy, return without changing live files;
do not stop any job to obtain it.

Ansible stages a fixed four-file allowlist and its SHA-256 manifest privately.
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

Pi5 `--check` passed: four files would change, live files were not replaced.
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
