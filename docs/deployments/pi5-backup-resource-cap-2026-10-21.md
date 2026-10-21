---
title: "Pi5 backup resource cap"
date: 2026-10-21
status: deployed-systemd
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
Semaphore task `#144` from commit `8e35a85`. A root-owned class wrapper and
argument-specific sudoers rules are now added; the executor defaults to
`systemd` mode. Backup work uses transient scopes with `CPUQuota=100%`,
`MemoryMax=1G`, and `IOWeight=50`. The portable mode remains available as an
explicit rollback via `BACKUP_PI_RESOURCE_MODE=portable`.

The approved Pi5 release playbook now includes the launcher alongside the
restricted executor and guard. The stronger `systemd` mode remains a follow-up:
first verify that a narrowly scoped root-owned wrapper is available, then
enable it through a separate reviewed release and inspect the next backup
class from `journalctl`.

The direct Pi5 probe confirmed `systemd-run` exists but a user scope returns
`Access denied`; the root-owned wrapper is the controlled path around that
restriction. The wrapper accepts only the five backup classes and invokes fixed
root-owned scripts; it cannot be used to run an arbitrary command.

## Verification

`backup/tests/test_pi_resource_cap.sh` proves portable execution, all systemd
properties, and strict failure when `systemd-run` is unavailable.

`backup/tests/test_scheduler_contract.sh` proves the executor requires the
launcher, the class wrapper and sudoers validation, and the health-repair
playbook publishes the launcher. The live release must still pass the Pi5
wrapper probe and one scheduled class before this change is considered fully
accepted.

## Rollback

Use the existing backup-client release receipt to restore the previous
executor and guard. Do not remove success markers or run retention manually
during rollback; wait for the next scheduled class and inspect its marker.
