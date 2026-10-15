# Runtime audit evidence gate

## Intent

Declarative policy export must not imply live health. Change its status to
`not_verified`. Inventory drift accepts only `mode: observed`, `status: ok`,
`complete: true`, a timezone-aware `observed_at` no older than 15 minutes,
and explicit unique string lists for hosts, services and routes.
Reject malformed, partial, future-dated and declarative evidence with exit 2.
Exit 1 means inventory drift; exit 0 means only inventory IDs match, not
resource health or verified backups. The full cross-host drift collector is
still pending; the restricted host-runtime observer is live.

Verification: CLI regression tests for policy export, invalid evidence,
fresh matching inventory and genuine drift. No runtime services are changed.
Public application documentation is unaffected by this internal gate.

## Verified result

The old CLI accepted declarative and stale reports with exit 0. Regression
tests reproduced that behavior before the fix. After implementation, all 15
tests under `automation/tests` pass in `homelab-automation-ee:local`.
The evidence test is included in GitLab validation. No full inventory collector
or production-health certification is claimed by this change.

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
- The previously observed `vigorous_napier` Alpine architecture probe was
  removed after confirming that it had no mounts, networks, secrets, configs,
  ports or environment and was not referenced by the runtime catalog. This
  cleanup is recorded in `runtime-catalog-reconciliation-2026-10-15.md`.
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

### Fresh Semaphore observations at 2026-10-15 16:19 +07:00

- VM100: task 49, template 4, success; observation timestamp
  `2026-10-15T09:19:05.381950+00:00`.
- Pi5: task 50, template 5, success; observation timestamp
  `2026-10-15T09:19:19.947610+00:00`.
- Both records passed the exporter contract: schema 1, timezone-aware
  observation, ten required probes, `scope: host_runtime_only`, and
  `inventory_complete: false`.
- The private controller artifacts were written outside the repository under
  mode-0700 directories with mode-0600 files. They are evidence for this
  checkpoint only and are not durable backups or a complete route/backup
  inventory.
- The first export attempt under `/tmp` was rejected by the private-artifact
  policy on macOS; the retry under the user's private home directory passed.
