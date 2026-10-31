---
type: Deployment Evidence
title: GitLab Redis network repair
description: Root-cause analysis and reversible network repair after the 2026-10-31 Redis update
generated:
  by: claude-code/opus-5.5
  at: "2026-10-31T00:00:00+07:00"
---

# GitLab Redis network repair — 2026-10-31

## Incident and root cause

GitLab authenticated API requests returned HTTP 500 while the GitLab Swarm
task, web health and readiness endpoints remained healthy. Rails logged
`Redis::CannotConnectError` with `getaddrinfo: Name or service not known` for
`redis-prod:6379/2`. The error surfaced while GitLab updated Personal Access
Token last-used state, so the API route exposed the Redis problem.

The Pi5 `redis-prod` container had been recreated from the base Compose file
only. It remained on `redis-prod_default` but lost its cross-host overlay
attachments. The current GitLab task was on `gitlab-net` (plus `pg-net` and
`edge-http-net`), while the Pi5 override declared only the older `homelab-net`
attachment. GitLab and Redis were healthy independently but had no shared
Docker DNS/network path. This was network/configuration drift, not a GitLab
image failure or a PAT-scope failure.

## Repair applied

1. Saved the previous Pi5 override as
   `/ssd-data/infra/redis-prod/docker-compose.override.yml.bak-codex-gitlab-redis-20261031`.
2. Attached the running Redis container to the existing attachable overlay with
   alias `redis-prod`:
   `docker network connect --alias redis-prod gitlab-net redis-prod`.
3. Updated the secret-free source
   `homelab-ops/migration/redis-prod-overlay.override.yml` and deployed the
   same file to the Pi5 Compose directory. Local and remote SHA-256 match.
4. Did not delete data, recreate Redis, change the Redis password, or change
   the Redis image. AOF/RDB data and the bridge attachment were preserved.

## Verification

| Check | Result |
|---|---|
| GitLab DNS | `redis-prod` resolves to Redis endpoint `10.0.5.31` on `gitlab-net` |
| TCP path | GitLab task can open `redis-prod:6379` |
| Redis auth/DB | GitLab secret-authenticated Redis DB `/2` returns `PONG` |
| GitLab health | Internal health `200`; readiness `200` |
| Public API without token | `/api/v4/version` and `/api/v4/user` return expected `401` |
| Config persistence | Merged Compose model includes `gitlab-net`; override checksum matches Pi5 |

The endpoint IP is expected Docker overlay DNS behavior and is not a public
address. Clients must continue to use `redis-prod`, never `10.0.5.31`.

## Rollback

To remove only the live attachment without touching Redis data:

```sh
ssh pi 'docker network disconnect gitlab-net redis-prod'
```

To restore the previous override, copy the dated backup back to
`/ssd-data/infra/redis-prod/docker-compose.override.yml`. Do not run the base
Compose file alone; that is the known way to reintroduce the drift.

## Follow-up gate

The PAT used during the failed preflight was exposed in a shell error. Its
value is intentionally not recorded here and must be revoked/rotated before
any GitLab project creation or repository push. After rotation, validate
`/api/v4/user`, then execute the per-repository mirror plan and record each
project URL, remote addition and push result in `PROJECTS.md`.
