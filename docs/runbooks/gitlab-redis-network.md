---
type: Runbook
title: GitLab ↔ Pi5 Redis network operations
description: Installation, update, verification and rollback procedure for the standalone Pi5 Redis container used by GitLab
generated:
  by: claude-code/opus-5.5
  at: "2026-10-31T00:00:00+07:00"
stale_after: "2027-01-29T00:00:00+07:00"
---

# GitLab ↔ Pi5 Redis network operations

This runbook records the live topology and the safe update procedure. The
current incident and exact repair evidence are in [GitLab Redis network repair](../deployments/gitlab-redis-network-repair-2026-10-31.md).

## Current topology

| Component | Location/runtime | Network contract |
|---|---|---|
| GitLab | VM100 Swarm service `gitlab_gitlab` | `gitlab-net`, `pg-net`, `edge-http-net`; Redis hostname `redis-prod`, DB `/2` |
| Redis | Pi5 standalone Compose container `redis-prod` | private Compose bridge plus external attachable `gitlab-net`; alias `redis-prod` |
| Redis data | Pi5 | `/ssd-data/infra/redis-prod/data`, AOF enabled, 1 GiB `noeviction` |
| GitLab config | VM100 bind mount | `/opt/apps/gitlab/config`; Omnibus sets `redis_host=redis-prod`, port `6379`, DB `2` |
| Redis source | local checkout | `/home/dungxbuif/workspace/projects/homelab-ops/migration/redis-prod-overlay.override.yml` |
| Redis runtime source | Pi5 | `/ssd-data/infra/redis-prod/docker-compose.yml` plus `docker-compose.override.yml` |

`gitlab-net` is a Swarm overlay marked `attachable`. A standalone Compose
container on Pi5 may join it. Docker's embedded DNS then resolves the alias
`redis-prod` to the Redis endpoint IP on that overlay. The endpoint IP is
internal and dynamic; application configuration must use the name, never the
observed IP.

## Correct installation/update procedure

1. Confirm the target image, current container ID, Redis data path, and current
   network membership. Do not start with a recreate.
2. Back up the RDB/AOF data and both Compose files. Keep the backup outside the
   data directory with a dated, reversible name.
3. Validate the merged Compose model on Pi5. Always pass both files.
4. Confirm that the merged model declares the external overlay and the
   `redis-prod` alias. If the existing container is missing the overlay,
   attach it before testing consumers.
5. From the GitLab task, verify Docker DNS and TCP connectivity. Then run an
   authenticated Redis DB2 probe without printing the password. GitLab
   health/readiness must pass before any project API operation.
6. Only after the backup and probes pass, recreate Redis with the base file
   and override file. Recheck network membership because a base-only Compose
   invocation is the known failure mode.
7. Re-run the GitLab API smoke test with a fresh, least-privilege PAT. Do not
   mark the mirror backlog unblocked from a web `200` alone; a valid-token
   `/api/v4/user` request is required.

## Verification commands

These commands expose no secret values:

```sh
# Pi5: container and network membership
docker inspect --format '{{json .NetworkSettings.Networks}}' redis-prod
docker network inspect gitlab-net --format '{{json .Containers}}'

# VM100: resolve and open the private Redis path from the GitLab task
docker exec <gitlab-task-container> getent hosts redis-prod
docker exec <gitlab-task-container> bash -lc 'timeout 3 bash -c "</dev/tcp/redis-prod/6379"'

# VM100: exercise GitLab's configured Redis client without printing the secret
docker exec <gitlab-task-container> gitlab-rails runner 'puts Gitlab::Redis::SharedState.with { |r| r.ping }'

# VM100: application health
docker exec <gitlab-task-container> curl -fsS -o /dev/null -w 'health=%{http_code}\n' http://127.0.0.1/-/health
docker exec <gitlab-task-container> curl -fsS -o /dev/null -w 'readiness=%{http_code}\n' http://127.0.0.1/-/readiness
```

Expected results are a `redis-prod` address on `gitlab-net`, TCP success,
`PONG`, and health/readiness `200`. A no-token public API `401` is expected;
it only proves the request reached GitLab, not that PAT-backed API use works.

## Rollback

If only the live attachment must be removed, disconnect the exact network and
leave Redis data and the bridge untouched:

```sh
docker network disconnect gitlab-net redis-prod
```

If the Compose source must be rolled back, restore the dated override backup,
then use the same two-file Compose invocation. Never restore by deleting the
Redis data directory and never run a broad network prune as a rollback.

## Do not do these things

- Do not run `docker compose up -d` from the base file alone.
- Do not replace `redis-prod` with `10.0.5.31` in GitLab configuration.
- Do not publish Redis `6379` to the public Internet or use the LAN host port
  as the VM100 service endpoint when the overlay path is available.
- Do not rotate or print the Redis secret in logs, shell history or docs.
- Do not run `docker network prune` while Swarm/Compose attachments are under
  investigation.
- Do not use an exposed GitLab PAT for project creation; revoke/rotate it and
  load the replacement only from the approved secret boundary.
