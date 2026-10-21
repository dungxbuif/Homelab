# Monitoring drift scheduler

Date: 2026-10-21
Status: deployed and verified

## Decision

Run the existing read-only active-target gate from VM100 once per day. VM100
can reach VictoriaMetrics on the Pi5 LAN address and already owns the Mezon
secret used by operational health notifications. The job must not restart
VictoriaMetrics, mutate scrape configuration, or infer service health from
historical `up == 0` series.

On a clean run it sends a compact success receipt; on a retired target or
query error it sends a failure receipt and exits non-zero so systemd and the
health dashboard can see the fault. The wrapper is bounded by systemd and
uses the existing notification helper; no new container is introduced.

## Verification plan

Contract tests must prove the wrapper calls the active-target gate and uses the
existing secret file without embedding a webhook. Production verification is
the timer state, a successful one-shot run, HTTP target evidence from
VictoriaMetrics, and a free VM100 backup lock.

## Production evidence

- VM100 installs both the wrapper and its dependency `audit-monitoring-targets.py`
  under `/opt/apps/homelab-backup/app/automation/maintenance/`.
- `homelab-monitoring-drift.timer` is enabled and active, with the next run at
  11:30 Asia/Ho_Chi_Minh (`04:30 UTC`).
- The first one-shot attempt failed closed with exit `2` because the dependency
  was missing from the release. The dependency was added to the release
  contract, redeployed with a rollback copy, and the next run completed with
  `Result=success` and `ExecMainStatus=0`.
- The repair playbook now installs the dependency before the wrapper, verifies
  both executable regular files before enabling the timer, and has a contract
  test for that ordering. This removes the previous deployment-order window
  that produced transient failure notifications.
- The wrapper uses the existing VM100 Mezon secret file and VictoriaMetrics
  target gate. It does not embed a webhook or alter scrape configuration.
