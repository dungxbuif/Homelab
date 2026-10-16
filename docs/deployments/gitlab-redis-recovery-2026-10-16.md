---
type: DeploymentRecord
title: "Recover shared Redis after stale Docker network removal"
timestamp: 2026-10-16T20:00:00+07:00
---

# Recovery intent

On 2026-10-16, GitLab returned HTTP 500 because its Rails process could not
resolve `redis-prod:6379`. The Pi5 `redis-prod` container was stopped with
exit 255: its saved container metadata referenced a removed Docker network ID.
The Redis bind data remains under `/ssd-data/infra/redis-prod/data`.

The recovery is limited to recreating the Redis container from the existing
Compose files. It must preserve the bind mount, password, append-only mode,
memory policy and database numbers; it must not delete or reinitialize Redis
data, change the LAN port, or create a second Redis instance.

## Verification contract

1. `docker compose config --quiet` succeeds on Pi5.
2. `redis-prod` is running and attached to `homelab-net` with alias
   `redis-prod` and its existing Compose bridge.
3. Authenticated `PING` and `INFO persistence` succeed without a data reset.
4. A temporary probe from the GitLab task resolves `redis-prod`, authenticates
   against database 2, and returns `PONG`.
5. GitLab Rails health/login and runner job-request endpoints recover; the
   affected pipeline is rechecked.

The recovery is intentionally performed before changing GitLab configuration:
the declared endpoint is already correct, while the backing Redis container
was not running.

## Result

Completed 2026-10-16. The Pi5 Compose service was recreated with
`--force-recreate` and the existing bind data was retained. The new container
is running with `redis-prod` on `homelab-net` at `172.30.18.209`; authenticated
`PING` returned `PONG`, `loading:0`, `aof_enabled:1`, and no Redis database was
reset. GitLab resolved `redis-prod` from its `homelab-net` task address and
subsequent Rails requests returned HTTP 200 for `/users/sign_in` and HTTP 204
for the GitLab Runner job-request endpoint.

Root cause was stale container network metadata after the Swarm overlay was
recreated. The durable Compose override and Redis endpoint remain unchanged;
future network recreation must recreate this standalone container as part of
the network recovery runbook.
