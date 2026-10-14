# Runtime audit evidence gate

## Intent

Declarative policy export must not imply live health. Change its status to
`not_verified`. Inventory drift accepts only `mode: observed`, `status: ok`,
`complete: true`, a timezone-aware `observed_at` no older than 15 minutes,
and explicit unique string lists for hosts, services and routes.
Reject malformed, partial, future-dated and declarative evidence with exit 2.
Exit 1 means inventory drift; exit 0 means only inventory IDs match, not
resource health or verified backups. The collector is still pending.

Verification: CLI regression tests for policy export, invalid evidence,
fresh matching inventory and genuine drift. No runtime services are changed.
Public application documentation is unaffected by this internal gate.

## Verified result

The old CLI accepted declarative and stale reports with exit 0. Regression
tests reproduced that behavior before the fix. After implementation, all 15
tests under `automation/tests` pass in `homelab-automation-ee:local`.
The evidence test is included in GitLab validation. No live collector or
production-health certification is claimed by this change.

## Host collection increment

Extend the read-only Ansible audit with running/stopped container summaries,
network summaries and one-shot container resource samples. Never collect
container environment, labels, mounts or command arguments. An optional
controller-side artifact directory stores mode-0600 JSON per host. These
artifacts have scope `host_runtime_only`, not a full drift inventory: routes,
backup integrity and catalog ID reconciliation remain separate requirements.
Verify syntax/lint, contract tests and real Pi5/VM100 bootstrap read-only runs.
Do not change host configuration or imply restricted-account rollout is done.

### Live bootstrap findings at 2026-10-14 16:28 UTC

- Pi5: read-only run succeeded (13 tasks, two controller artifact writes),
  Docker 28.4.0, root disk 37%, 4 GiB swap with about 1.8 GiB used;
  21 running containers out of 26 retained containers.
- VM100: succeeded (12 tasks, one controller artifact write), Docker 29.1.3,
  root disk 75%, about 48.7 GiB available, 8 GiB swap with about 1.2 GiB used;
  27 running containers out of 93 retained containers at sample time.
- Swarm still lists `orangepizero3 Down Active`; do not remove membership
  without checking placement and recovery requirements.
- `vigorous_napier` uses Alpine 3.22, created 2026-10-01 16:08 UTC, restart
  condition `any` with 5-second delay and no maximum attempts. Its tasks
  repeatedly exit 0. Ownership/purpose must be checked before removal.
- CouchDB sampled about 146% CPU on Pi. One sample does not establish sustained
  load; no resource changes were made on that evidence alone.
- Runtime catalog omits live applications/monitoring entries. Do not label
  omitted services retired or remove them based only on catalog absence.

Private artifacts: `/tmp/homelab-audit-20261014/pi5.json` and `vm100.json` on
the Mac controller, mode 0600 in a mode-0700 directory. They are temporary,
not durable backup artifacts and not a complete route/backup audit.

Live testing found `/usr/bin/swapon` does not exist on Pi. Use `/proc/swaps`
instead. VM100 transport succeeded with JSON-encoded Ansible extra vars and
explicit local key/IdentityAgent=none; malformed shell-style extra vars caused
an earlier invalid-hostname attempt. The host itself remained reachable.
Seven Ansible contract tests and 15 automation tests pass in the local EE;
ansible-lint passes the modified audit playbook. Controller transport remains
a bootstrap exception, not the intended restricted Semaphore identity.
