---
title: "Pi5 backup resource cap"
date: 2026-10-21
status: prepared-not-deployed
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

This change is prepared and contract-tested in the repository. It is **not
deployed to Pi5 yet** because the current direct write transport is unavailable
and the observer SSH key is read-only. No production backup schedule was
changed in this step.

The approved Pi5 release playbook now includes the launcher alongside the
restricted executor and guard. Once the Semaphore Pi5 release identity is
available, release it as one atomic client change and verify the next backup
class from `journalctl` before enabling `systemd` mode.

## Verification

`backup/tests/test_pi_resource_cap.sh` proves portable execution, all systemd
properties, and strict failure when `systemd-run` is unavailable.

`backup/tests/test_scheduler_contract.sh` proves the executor requires the
launcher and the health-repair playbook publishes it.

## Rollback

Use the existing backup-client release receipt to restore the previous
executor and guard. Do not remove success markers or run retention manually
during rollback; wait for the next scheduled class and inspect its marker.
