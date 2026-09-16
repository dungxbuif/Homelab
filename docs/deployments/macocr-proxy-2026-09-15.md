# macocr-proxy Swarm cutover (2026-09-15)

## Intent and boundaries

Move only the OCR HTTP proxy from VM100 Compose with host port `18080` to a
portless VM100 Swarm task on `homelab-net`. Keep the native OCR engine on the
Mac mini `10.10.0.6:8787`, the existing Pi5 databases/Redis, and the old
Compose image/configuration as a stopped rollback path. No app source or data
was changed. No user OCR document was submitted as a synthetic test.

## Runtime and route

- Service: `macocr-proxy`, one VM100-constrained Swarm replica; image
  `homelab/macocr-proxy:vm100-20260910`, local image ID
  `sha256:6e99e8d01657e536f4276de4faec1acc55102988ed41bf6e511ac378417b0d0c`.
- The 19 environment entries, mounts (none), and image were checked for parity
  with `vm100-macocr-proxy` without printing secrets. Health command is
  `wget -qO- --timeout=3 http://localhost:8080/healthz`.
- Orange Pi file route `ocr.dungxbuif.com` targets
  `http://tasks.macocr-proxy:8080`; route backup is
  `/opt/edge/traefik/dynamic.yml.bak-macocr-proxy-swarm-20260915-141500`.
  Source/live dynamic config SHA-256 after cutover:
  `736349698c5b4847349f5dabd00d2e146663509aa2ffacd6c563017154a0c015`.
- Former Compose project `macocr_proxy`, service `macocr-proxy`, container
  `vm100-macocr-proxy` was stopped at 2026-09-15 14:26:41 UTC. VM100 TCP
  `18080` was confirmed closed; Compose config/image remain for rollback.

## Verification and observations

### Datastore endpoint follow-up

After the route cutover, only OCR service `DATABASE_URL` host/port changed
from Pi5 LAN PgBouncer mapping `10.10.0.5:5432` to overlay
`pgbouncer:6432`, preserving database, user, password, and query options.
The proxy task returned to healthy state; a private PostgreSQL `SELECT 1`,
native Mac `/capacity 200`, public OCR `/healthz 200` and `/docs/ 200`
all passed after restart. Redis URL was not changed in this step.

### Redis endpoint follow-up

Pi5 `redis-prod` remains its original Compose service with the same `/data`
bind, AOF, password, and LAN `16379` mapping. The secret-free Compose override
at `migration/redis-prod-overlay.override.yml` is installed on Pi5 as
`/ssd-data/infra/redis-prod/docker-compose.override.yml`; it retains the
project default bridge and adds external `homelab-net` with DNS alias
`redis-prod`. Merged Compose config was checked before controlled recreate;
afterwards Redis was running on both networks, same data bind, AOF enabled,
and authenticated `PING` returned `PONG`. OCR task AUTH also returned `PONG`
through `redis-prod:6379` before the URL change. Only OCR `REDIS_URL`
host/port changed from `10.10.0.5:16379/0` to `redis-prod:6379/0`;
credential and DB index were preserved. After OCR restart, task health,
authenticated `PONG`, DB `SELECT 1`, Mac `/capacity 200`, and public OCR
routes passed. MyPocket URLs were left unchanged while `money` is in active
development. No Redis data was cleared or LAN port closed.

- Four timed public/cross-route rounds and a check after more than ten minutes
  returned `200` for OCR `/healthz`, OCR `/docs/`, Family Tree `/login`,
  MezonHook `/`, Homepage `/`, and n8n `/healthz` (or the expected pgAdmin
  redirect). OCR task remained healthy after old Compose stopped.
- The Swarm task network namespace reached Mac native OCR
  `http://10.10.0.6:8787/capacity` with HTTP `200` after the operator started
  the native process on LAN port `8787`. Earlier `connection refused` logs
  were from the native process being down; no such warning appeared after
  restart in the three-minute post-start log window.
- PostgreSQL `SELECT 1` through the current OCR database URL passed.
  The OCR URL password matched the Redis server credential; authenticated
  `redis-cli --askpass PING` from the task network namespace returned `PONG`.
  `redis-cli -u "$REDIS_URL"` reported `WRONGPASS`/`NOAUTH` in both the old
  and new containers, so that URL-based CLI probe is not an app regression or
  a valid authenticated readiness check for this environment.
- This verifies proxy health, routing, native capacity, DB read, and Redis
  connectivity. End-to-end OCR processing was not exercised with a document.

## Rollback

If OCR public behavior regresses, restore the Orange Pi route backup to
`10.10.0.31:18080`, wait for route reload, then restart only the old Compose
service. Check `/healthz`, `/docs/`, and native `/capacity` before removing the
Swarm task. Do not run a fresh Orange Pi helper on `homelab-net`: previous
canaries observed unresolved ARP in the long-lived Traefik task and transient
cross-route `502` responses after such an attach.
