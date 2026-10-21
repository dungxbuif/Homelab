# MyPocket API resource canary

Date: 2026-10-21

## Change

Only the production Swarm service `mypocket-api` was updated. Its image,
environment, networks, route, and database/Redis endpoints were unchanged.
The worker was intentionally left uncapped because it has no HTTP health
contract and needs queue-latency evidence first.

```text
CPU:    1.00 vCPU
Memory: 1 GiB
Order:  stop-first
```

The update kept one-task parallelism and rollback-on-failure. The API has no
bind mount, so no persistent writer overlap was introduced.

## Verification

- Swarm update state: `completed` / `update completed`.
- New task: healthy on `vm100-prod`.
- `https://money.dungxbuif.com/api/v1/health`: HTTP 200,
  `{"data":{"status":"ok"},"meta":null}`.
- The route returned HTTP 502 briefly during task warm-up, then recovered.
- Worker: unchanged and still running without a cap pending queue metrics.

## Follow-up

Capture worker queue depth/latency and memory high-water mark before applying a
separate worker limit. Do not treat the API limit as the worker limit.
