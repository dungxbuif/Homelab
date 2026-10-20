---
type: Deployment Note
title: "Lock-aware backup health check"
description: "Prevent false backup-health failures while an approved backup unit is still running"
date: 2026-10-20
status: deployed
---

# Lock-aware backup health check

## Intended behavior

The read-only health check must not report a failed health state merely because
the shared backup lock is held by a valid backup or retention unit. It will
report the active unit and runtime as `state=running runtime=Ns`, and return
success while the runtime is within the class-specific limit. A held lock with
no recognized active unit, or a recognized unit beyond its limit, remains a
health failure. Existing stale-marker, failed-unit, free-space, and Pi health
checks remain authoritative.

## Runtime limits

| Class | Limit |
|---|---:|
| databases | 2 hours |
| database-instances | 30 minutes |
| gitlab | 5 hours |
| rustfs | 90 minutes |
| retention | 90 minutes |

The limits are overridable for test and operator environments through one
environment variable per class. The existing global six-hour fallback remains
for an active unit whose class is not listed.

## Verification plan

1. Add shell tests for an in-limit active unit, an over-limit active unit, and
   a lock held without an active backup unit.
2. Run the focused health test suite and scheduler contract tests.
3. Deploy only the health script through the existing reviewed health-repair
   path, then run the read-only health command on VM100.
4. Confirm that no backup, retention, restore, or data cleanup operation is
   started by the change.

## Result

Deployed to VM100 and Pi5 on 2026-10-20. The VM100 systemd health service
returned `Result=success` with exit status `0`; the restricted Pi health
command also returned success. Both hosts use the same script digest:
`837f566d6d55e78ddf4280f5cd5f506a98b1e551daaa8931cdd2c2d46bd875b5`.

The first VM100 probe exposed a real `fs.protected_regular` permission issue:
the service was trying to open the shared lock with truncating write access.
The script now creates the lock only when absent and opens an existing lock
read-only before calling `flock`. The previous script was retained in a
timestamped `.bak-lock-aware-*` file on each host.

The database runtime limit was raised to two hours on 2026-10-20 after comparing
the last successful runs, which completed in approximately 92 to 104 minutes.
This keeps the lock-aware behavior while preventing the health timer from
classifying a normal PostgreSQL plus CouchDB export as overlong. The broader
schedule/cadence changes in Phase 2 remain open; this deployment covers the
lock-aware health behavior and its runtime calibration.
