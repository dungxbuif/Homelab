---
type: Deployment Note
title: "Configuration backup readiness"
description: "Live inventory and safety gates for the encrypted configs backup class"
date: 2026-10-20
status: remote-upload-and-restore-verified-timer-enabled

Operational note (2026-10-21): the first `configs` run failed closed because its
Restic repository had not been explicitly initialized. A native local Restic
bootstrap was created and copied to Drive with rclone; the first production
snapshot is `d4ea082a8334cd8baab64c7afa1daf37d98a1eca7661e6b149eefc54030a7025`.
Restic integrity verification passed, and a local-mirror restore of 44 files
and 361 MiB passed checksum verification. The timer is now enabled after these
gates. VM100-to-Pi5 SSH commands have a bounded timeout, and read-only metadata
and restore operations use `--no-lock` after upload integrity verification.
---

# Configuration backup readiness

## Live inventory

The active Pi5 edge mounts are under `/home/dungxbuif/edge`, not the historical
`/ssd-data/infra/traefik` and `/ssd-data/infra/adguard` paths:

- Traefik: `/home/dungxbuif/edge/traefik/traefik.yml`, `dynamic.yml`, and its
  ACME storage where present
- AdGuard Home: `/home/dungxbuif/edge/adguard/conf` and `work`
- Rathole: `/home/dungxbuif/edge/rathole/rathole.toml`
- Pi5 stack declarations and runtime env files: selected files below
  `/ssd-data/infra`, excluding backup directories, historical stacks, data
  volumes, caches, and source checkouts

VM100 has active application declarations under `/opt/apps`, including Compose
files, `.env` files, NetBird configuration, and app-specific configuration.
The collector must use an explicit allowlist and exclude run data, database
volumes, build caches, old release directories, and generated backup runs.

## Safety gates before enabling

1. The Pi5 collector must fail if any required active edge source is missing;
   a partial group must never produce a successful class marker.
2. VM100 and Pi5 collection must be combined into one atomic run before Restic
   upload and Mezon post-check.
3. Retention, health, local cleanup, and restore admission must recognize the
   `configs` class before its timer is enabled.
4. The encrypted Restic repository is the only remote destination. The staging
   directory is mode `0700`, sensitive files are mode `0600`, and cleanup runs
   only after a verified remote post-check.
5. A first run must be inspected and restored into a scratch directory before
   the timer is enabled.

The older `codex/backup-deadman-configs` branch is a reference only. It is not
safe to deploy because it has stale Pi paths, no VM100 collector, and incomplete
retention/health integration.

## Current evidence

`backup/scripts/validate-config-sources.py` is a standalone, secret-free
fail-closed validator. It passed focused local tests and was run read-only on the
live hosts:

- Pi5: 5 required sources present, 5 optional sources present
- VM100: 5 required sources present, 15 optional sources present

The collector and encrypted upload integration are now wired locally. The
`configs` Restic repository maps to `homelab-backups/configs`, the policy is
14 daily / 8 weekly / 12 monthly, restore admission accepts the class, and
VM100 retention verifies and cleans its local config runs after a successful
marker. The timer remains disabled until one manual upload, remote post-check,
and scratch restore are verified.

The collector is implemented in
`backup/scripts/run-configs-backup.py` and wired behind the explicit
`BACKUP_CONFIGS_PI_ARCHIVE` gate in `run-class.sh`. It is deployed but not
enabled; the fixed Pi5 archive exporter, forced-command allowance,
`configs` Restic mapping, cleanup, retention, and restore admission are now
implemented. The first manual upload, remote post-check, and scratch restore
remain pending until the current long-running retention check releases the
global lock.

The first real `configs` service reached Restic preflight and failed closed
because `homelab-backups/configs` does not exist yet. Implicit repository
initialization is refused; the next controlled step is an explicit `restic
init`, followed by rerunning the class and verifying the snapshot.

The Pi exporter preserves the active `root:root 0600` AdGuard YAML. Because
the backup account cannot read that file directly, it uses the already-present
`alpine:3.22` image with `--network none`, mounts only the two source roots
read-only, and asks the BusyBox tar for the exact allowlist. The Docker socket
is never mounted and no temporary Pi archive is left behind.
