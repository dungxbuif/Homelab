# External heartbeat on VPS

Date: 2026-10-21
Status: deployed and verified

## Decision

Run the heartbeat on the public VPS, outside VM100 and Pi5. Every five minutes
it checks the public HTTPS path for the homepage, RelayHub and OCR health
endpoint. It sends one Mezon message only when the aggregate state changes
between healthy and failed, then records the state locally on the VPS.

The check is read-only: it does not inspect Docker, change Traefik/Rathole,
open a port, or expose a database. The webhook is supplied by a mode-0600 VPS
file and is never stored in Git.

## Verification

- Contract tests must pass without a live webhook.
- VPS verification must show the timer enabled/active, a successful one-shot
  run, and a state file containing `healthy`.
- A controlled failure test should use an environment override or a temporary
  URL list and must not alter public routing.

## Production evidence

- VPS timer `homelab-external-heartbeat.timer` is enabled and active, with a
  five-minute cadence.
- One-shot service completed with `Result=success` and `ExecMainStatus=0`.
- The public probes passed: `https://dungxbuif.com/`,
  `https://relayhub.dungxbuif.com/`, and
  `https://ocr.dungxbuif.com/healthz` all returned `HTTP 200`.
- VPS state is `healthy`; the Mezon webhook is stored at
  `/etc/homelab-external-heartbeat/mezon-webhook` with mode `0600`.
- Rollback copy: `/root/rollback-external-heartbeat-20261021-001636`.
