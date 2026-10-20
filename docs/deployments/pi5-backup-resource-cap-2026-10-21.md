---
title: "Pi5 backup resource cap"
date: 2026-10-21
status: deployed-portable
---

# Pi5 backup resource cap

## Decision

The Pi5 remains the operator-approved home for AdGuard, Traefik and Rathole,
and currently still executes the shared `databases` and `rustfs` backup
classes. Until retention and deep verification move to VM100, every Pi5
backup command must pass through one bounded launcher.

`automation/backup-runner/run-pi-capped.sh` has two modes:

- `portable` (default): lowers CPU scheduling priority with `nice` and moves
  I/O to the idle class with `ionice -c 3`. This is compatible with the
  existing forced-command user and does not require root or a user systemd
  manager.
- `systemd`: starts a transient scope with `CPUQuota=100%`, `MemoryMax=1G`
  and `IOWeight=50`. This mode is the target when a root-owned, narrowly
  scoped systemd wrapper is enrolled on Pi5.

The launcher validates all limits before execution and fails closed when
`BACKUP_PI_RESOURCE_MODE=systemd` is selected but `systemd-run` is absent.
The executor refuses to run if the launcher is missing, so a partial release
cannot silently restore an unrestricted backup path.

## Current state

The bounded launcher and restricted handlers were deployed to Pi5 by
Semaphore task `#144` from commit `8e35a85`. The task finished with
`unreachable=0`, `failed=0`, and published all three files. The current
runtime uses the compatible `portable` mode by default, so backup work runs
with `nice` and `ionice -c 3` without requiring a privileged cgroup manager.
No production backup schedule was changed.

The approved Pi5 release playbook now includes the launcher alongside the
restricted executor and guard. The stronger `systemd` mode remains a follow-up:
first verify that a narrowly scoped root-owned wrapper is available, then
enable it through a separate reviewed release and inspect the next backup
class from `journalctl`.

## Verification

`backup/tests/test_pi_resource_cap.sh` proves portable execution, all systemd
properties, and strict failure when `systemd-run` is unavailable.

`backup/tests/test_scheduler_contract.sh` proves the executor requires the
launcher and the health-repair playbook publishes it.

## Rollback

Use the existing backup-client release receipt to restore the previous
executor and guard. Do not remove success markers or run retention manually
during rollback; wait for the next scheduled class and inspect its marker.
