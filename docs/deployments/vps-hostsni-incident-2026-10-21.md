---
type: Deployment
title: "VPS HostSNI incident forensic result"
description: "Read-only investigation of the 2026-10-20 VPS gateway outage and the guarded change contract"
timestamp: 2026-10-21T00:00:00Z
---

# VPS HostSNI incident forensic result

## Scope

This note records the read-only investigation of the outage reported after
removing `pgadmin.dungxbuif.com` from the VPS `/root/gateway/dynamic.yml`
`HostSNI` allow-list. No VPS configuration was changed during this
investigation.

## Evidence

- The known-good file and the retained failed file are both 25 lines and both
  pass `docker compose config --quiet` on the VPS.
- Their SHA-256 values differ only because the failed file removes the one
  `HostSNI(`pgadmin.dungxbuif.com`)` term from the shared
  `rathole-passthrough` rule. The YAML structure and every other hostname are
  unchanged.
- `gateway-traefik` bind-mounts the single host file at
  `/etc/traefik/dynamic.yml` and has the file provider watcher enabled.
- The failed window was not a container restart: the gateway container stayed
  up and its access log continued serving GitLab's separate Docker route.
- Restoring the known-good content in place recovered the shared routes within
  seconds. The file-provider access path therefore remains the most plausible
  failure boundary, but historical logs do not contain a provider reload error
  that proves the exact kernel/watch event.

## Root-cause classification

The incident is classified as **unsafe live file-provider mutation**, not a
bad hostname token or invalid YAML. The shared TCP router is a single
allow-list for the Rathole path; if Traefik temporarily observes an empty,
partial, or deleted bind-mounted file while a writer edits it, all shared
Rathole-backed sites can disappear together. A valid final file does not make
that transition safe.

This is a bounded conclusion: the historical event cannot be reproduced from
the retained logs alone, so the exact watcher event is not claimed as proven.

## Guard contract

Future HostSNI edits must:

1. read and hash the exact expected source;
2. parse the proposed YAML and verify that exactly one approved term changed;
3. validate the Traefik/provider configuration before touching the live file;
4. preserve the bind-mounted inode with an in-place write;
5. keep a timestamped rollback copy and verify the post-write hash; and
6. run a bounded route smoke check, restoring the backup on any failed check.

The existing GitLab-specific helper satisfies only part of this contract. The
generic guard added in this rollout is the required path for future allow-list
edits; manual `sed`, `mv`, `cp` or unguarded editor changes are prohibited.

Example dry-run from the VPS gateway (the expected hash must be obtained from
the approved change record):

```sh
python3 automation/scripts/vps-hostsni-edit.py \
  --path /root/gateway/dynamic.yml \
  --static-config /root/gateway/traefik.yml \
  --expect-sha256 <approved-current-sha256> \
  --remove-host example.dungxbuif.com
```

Add `--apply` only after the dry-run is reviewed. The command creates a
timestamped backup and preserves the live file inode. Use `--restore
/root/gateway/dynamic.yml.bak-vps-hostsni-<timestamp>` for the bounded rollback
path, also with `--static-config` so the restored candidate is checked first.

## Current state

The live VPS file matches the known-good SHA-256 recorded in the incident
evidence. The failed copy remains preserved under
`/root/firewall-backup/dynamic.yml.broken-attempt` for forensic comparison.

The generic guard contract test now passes in a temporary Python environment
with `PyYAML` (`6 tests, OK`), including a subprocess check that a mismatched
expected hash is rejected before the provider check. A live VPS dry-run and route smoke check still
require an approved current hash and operator access; this note does not claim
that historical watcher behavior has been reproduced.
