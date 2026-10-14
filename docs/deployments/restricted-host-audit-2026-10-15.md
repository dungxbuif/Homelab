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

The Semaphore-side playbook is prepared at
`automation/semaphore/playbooks/host-audit.yml`, but UI key/inventory/template
registration and execution are still pending publication. Passing collection
does not mean the observed workloads are healthy or fully inventoried.

`bootstrap-host-audit.mjs` prepares the UI resources with dry-run by default,
duplicate-name rejection and existing-configuration checks. Its live dry-run
found no pre-existing observer resources. Only the public SSH key is tracked.
CI must run both observer tests and the forced-command guard tests before the
new UI source is accepted.
