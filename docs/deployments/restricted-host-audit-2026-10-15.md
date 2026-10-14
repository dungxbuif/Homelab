# Restricted host audit collector

Next control-plane slice: a fixed read-only host collector, suitable for a
root-owned forced-command helper. It accepts no arguments or arbitrary commands,
uses absolute executable paths and a fixed Docker socket, and emits structured
JSON containing selected container, network, resource, swap, disk and socket
observations. Never collect inspect output, environment variables, logs, process
arguments, Docker credentials, or file contents beyond /proc/meminfo and swaps.

Each command has a bounded timeout; any collection failure makes the report
incomplete and the process nonzero. Preserve failed probe names/error classes
without dumping arbitrary stderr. Report `scope=host_runtime_only` and
`inventory_complete=false`; this cannot prove firewall, routing, backup integrity
or application correctness. Tests cover allowed commands, fail-closed evidence,
no caller-controlled executable paths and no argument acceptance.

Do not install or grant sudo until tests pass and the collector is reviewed.
Bootstrap is read-only and introduces no new network, port or service restart.
The existing backup-health identity keeps its original single-command scope.

## Implemented and verified

`automation/scripts/host-observer.py` now implements eight fixed probes with
30-second per-command timeouts, a clean environment and no shell invocation.
Five unit tests pass, covering command boundaries, argument rejection, missing
executables, command failures and timeouts. The initial three tests failed before
the collector existed. Errors omit command stderr and partial command stdout.

Read-only execution on VM100 through the existing bootstrap SSH account at
2026-10-14 18:27 UTC returned exit 0 and all eight observations. No file was
installed remotely and no new sudo or SSH permission was granted. This does not
yet establish a restricted production execution path or Semaphore UI template.
Public application documentation is unaffected by this internal collector.

Observed follow-ups, not automatic remediation:
- Root filesystem had 69,341,192,192 bytes available (67 percent used).
- MemAvailable was 8,623,376 KiB; configured swap was approximately 8 GiB with
  only 21,480 KiB used. This single sample is not a peak-load capacity test.
- Many containers showed the host memory ceiling instead of an explicit lower
  limit; reconcile service ownership and workload requirements before changing.
- `vigorous_napier` repeatedly exited successfully and was recreated. Determine
  its owner and intended service mode before removing or modifying it.
- Old exited containers and legacy network names remain; existence alone is not
  sufficient proof that their volumes or networks can be deleted.

Next gates: review helper security, install a root-owned copy with a dedicated
forced-command identity, register the read-only UI task, and verify forbidden
commands fail while normal observations succeed. Do not reuse or widen the
backup-health identity.

## VM100 enrollment decision

Use a separate `homelab-observer` account and key. A root-owned forced-command
guard accepts exactly `host-audit` and invokes only the root-owned Python
collector without arguments as `ubuntu` through sudo. The collector uses Python
isolated mode and no local imports. The account has no Docker group membership;
its home and authorized_keys are root managed. No root shell is granted.
Enrollment requires an explicit approval variable and an Ed25519 public key.
Verify forbidden SSH commands return 2, the allowed command produces valid JSON,
and a second Ansible application is unchanged. Register the Semaphore task only
after these access checks. This does not yet cover Pi, VPS or Mac.

### Live enrollment acceptance

The account and root-owned helpers were installed through
`automation/ansible/playbooks/host-audit-enroll.yml`. Initial application:
8 tasks, 6 changed, no failures. Second application: 8 tasks, 0 changed,
no failures. Ansible-lint passed its production profile. The two guard tests
failed before implementation and passed afterwards; the five collector tests
also pass.

Using the dedicated key with strict pinned host trust and no SSH agent:
`id` and `host-audit extra` both returned 2; `host-audit` returned 0 with
`collection_complete=true` and all eight probes. Private key is ignored at
`credentials/semaphore-host-audit`, never committed. No application restart,
port, network, or backup-health permission changed.

The Semaphore-side playbook is published at
`automation/semaphore/playbooks/host-audit.yml`. UI enrollment and acceptance
are recorded below. Passing collection
does not mean the observed workloads are healthy or fully inventoried.

`bootstrap-host-audit.mjs` prepares the UI resources with dry-run by default,
duplicate-name rejection and existing-configuration checks. Its live dry-run
found no pre-existing observer resources. Only the public SSH key is tracked.
CI must run both observer tests and the forced-command guard tests before the
new UI source is accepted.

### Semaphore acceptance

Source published as GitLab commit `99301f9a42dd6b61130e4a215177e7838266ef62`.
Bootstrap created key 4, inventory 3 and template 4, named
`Inspect VM100 runtime (read only)`. Running bootstrap again verified and reused
the same resources. Task 19 ran on runner 1 against that exact commit and
succeeded: 4 tasks, changed=0, unreachable=0, failed=0. The report contains
`collection_complete=true`, `inventory_complete=false`, scope `host_runtime_only`.
This is a working UI audit path for VM100 only, with no general admin SSH key
in the runner. Pi/VPS/Mac enrollment and full inventory reconciliation remain.

## Pi5 extension plan

The unmodified collector ran read-only on Pi5 and all eight probes succeeded.
Extend enrollment only to the fixed Pi5/VM100 transport targets. Pi's guard must
run the same root-owned collector as `dungxbuif`, not `ubuntu` and never root.
Use the existing observer role key for these two hosts only; backup-health trust
remains separate. Keep explicit target-to-user/guard mappings and test both guards.
Verify denial of arbitrary commands, complete JSON output and idempotent Ansible
enrollment before adding Pi to Semaphore. This cannot enroll VPS or Mac.

Pi enrollment preflight exposed an Ansible privilege-escalation incompatibility:
`sudo` resolves to sudo-rs 0.2.13, and both normal and no-PTY Ansible become
attempts timed out waiting for a prompt. The same `id -u` request with identical
credentials and `ansible_become_exe=/usr/bin/sudo.ws` returned 0 immediately.
The existing setuid `/usr/bin/sudo.ws` is used only for this playbook on Pi;
system sudo alternatives and interactive SSH configuration are unchanged.
The Pi Ed25519 host public key was read over the existing trusted connection
and pinned alongside VM100, rather than accepting an unverified keyscan result.

Pi visudo additionally rejected a sudoers fragment without a final newline;
the copy content now uses a YAML literal block with its line terminator.
Validation failed before installation, so no invalid sudoers file was applied.
Enrollment then completed; the subsequent run reported 8 tasks, 0 changes,
0 failures. SSH using the observer role key rejected `id` and `host-audit extra`
with exit 2, while `host-audit` returned complete JSON and exit 0.
All three guard tests and Ansible production lint passed. The registration script
now accepts an explicit `--pi5` selector; default VM100 dry-run still resolves
existing resources 4/3/4 unchanged.

Pi registration created key 5, inventory 4, template 5 (`Inspect Pi5 runtime
(read only)`), and a second bootstrap apply reused the same IDs. Semaphore
task 24 ran commit `968298b1dfdf488fc19302b74bc1804e116d3df5` on runner 1 and
passed all four tasks, changed=0, unreachable=0, failed=0. Both Pi5 and VM100
now have working restricted UI audit paths. VPS/Mac coverage, routing/firewall
verification and peak-load sizing remain separate unfinished requirements.
