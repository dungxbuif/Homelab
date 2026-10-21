# OpenClaw resource canary

Date: 2026-10-21

## Change

The production Swarm service `openclaw` on VM100 was updated without changing
its image, bind mounts, networks, environment, or routing. The service now has
these Docker limits:

```text
CPU:    1.00 vCPU
Memory: 2 GiB
Order:  stop-first
```

`stop-first` was retained because OpenClaw owns persistent bind mounts for its
state, auth-profile secrets, and workspace. The update uses the existing
rollback-on-failure policy and a one-task parallelism of one.

## Verification

- Swarm update state: `completed` / `update completed`.
- New task: running and healthy on `vm100-prod`.
- Image: unchanged `homelab/openclaw:vm100-20260912`.
- `https://openclaw.dungxbuif.com/`: HTTP 200.
- `/healthz`: HTTP 200 with `{"ok":true,"status":"live"}`.
- `/readyz`: HTTP 200 with `{"ready":true}`.

The route returned HTTP 502 briefly while the new task was starting. It
recovered after the container health check passed; no rollback was required.

## Follow-up

Observe memory high-water mark, restart count, Telegram polling, and gateway
latency before changing the limit again. The next resource canary must remain
independent of this one.
