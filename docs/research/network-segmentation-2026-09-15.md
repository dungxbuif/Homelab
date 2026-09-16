# Swarm network audit and segmentation proposal (2026-09-15)

## Scope and observed topology

Membership/IP audit followed the verified VM100 routing and datastore
endpoint cutovers. At the post-GitLab-HTTPS stage, 18 Swarm services, including `edge_traefik`,
`edge_rathole`, `edge_adguardhome`, VM100 HTTP apps, and `mypocket-worker`,
are attached to the same attachable overlay `homelab-net`. None of the
VM100 Swarm HTTP apps publishes an HTTP host port. Edge publishes DNS
`53/tcp+udp`, AdGuard UI `81/tcp`, and Traefik `80/tcp`, `443/tcp+udp`
on Orange Pi.

The 2026-09-16 Registry trial added a third GitLab tunnel client on
`homelab-net`. VM100 SSH inventory now shows 16 Swarm tasks plus two BDS
standalone containers. Including the three edge services gives an expected
19 Swarm services, but manager/edge inventories were not refreshed during
the documentation audit. Do not confuse this expected total with a fresh
manager-side `docker service ls` observation. The proposed network split
below remains unimplemented.

Pi5 standalone `postgres`, `pgbouncer`, `redis-prod`, RustFS, Registry,
CouchDB, pgAdmin, and LibreSpeed are also attached to `homelab-net`.
Pi5 telemetry/exporters stay only on `proxy_net`. `redis-prod` additionally
keeps its Compose bridge `redis-prod_default` and persistent `/data` bind.
Pi5 RelayHub test API, worker, NATS, and Postgres containers use only
`relayhub_relayhub` and are not the VM100 public bootstrap service or shared
production datastore. The test API currently publishes Pi5 host port 8080;
confirm development users before closing it.

VM100 `bds-app` is attached to `homelab-net` and `bds-tunnel-net`, while
`bds-cloudflared` is attached **only** to `bds-tunnel-net`; keep that
isolation. The Orange Pi file provider targets `tasks.<service>` on
`homelab-net`, not Swarm labels or a remote Docker socket proxy.

## Connection matrix and literal IP classification

| Path | Current network/endpoint | Evidence and boundary |
|---|---|---|
| Orange Pi Traefik -> VM100 HTTP apps | `homelab-net`, `tasks.*` | Active dynamic file and public probes for Homepage, OCR, Family Tree, MezonHook, n8n; other app flows were not exercised in this audit |
| n8n, Family Tree, OCR -> Pi5 PostgreSQL | `homelab-net`, `pgbouncer:6432` | Each client/task namespace returned `SELECT 1` after endpoint update |
| OCR -> Pi5 Redis | `homelab-net`, `redis-prod:6379/0` | Authenticated `PING` returned `PONG` after durable Compose network join |
| BDS cloudflared -> BDS app | `bds-tunnel-net` only for tunnel; app also joins `homelab-net` | Docker membership, no LAN IP literal in running env; application traffic not replayed here |
| MyPocket API/worker -> datastore | `homelab-net`, `pgbouncer:6432/mypocket`, `redis-prod:6379/1` | Each task namespace passed authenticated `SELECT 1`/`PONG`; API healthy, worker ready, public money 200 after ordered service updates |
| OpenClaw public ingress -> Gateway | VPS/Rathole -> edge -> `homelab-net` | Public 200 after narrowing trusted proxy CIDR; ingress overwrites client-supplied XFF, but the forwarded client is the tunnel bridge `172.18.0.1`, not the true Internet IP |
| GitLab -> Pi5 PostgreSQL/Redis | `homelab-net`, direct `postgres:5432/gitlabhq_production`, `redis-prod:6379/2` | VM100-constrained service and secret-mounted temporary probes passed `SELECT 1`/`PONG`; GitLab internal login 200 and `gitlab:check` Gitaly/Shell/Sidekiq/migrations OK; public HTTPS is temporarily VPS-routed |
| VPS Git SSH -> VM100 GitLab | Isolated Rathole server VPS `7001`/`2222` -> portless VM100 Swarm `gitlab-ssh-tunnel_client` -> `tasks.gitlab_gitlab:22` on `homelab-net` | Noise control channel established; public SSH host key fingerprint matches GitLab container. VPS server does not join the overlay; client uses static VPS address only for the external tunnel endpoint. |
| VPS GitLab HTTPS -> VM100 GitLab | VPS Traefik Docker label -> `gitlab-https-rathole-server:8085` on VPS `gateway-network`; VM100 portless `gitlab-https-tunnel_client` -> `tasks.gitlab_gitlab:80` on `homelab-net` | VPS server publishes only control `7002`, never joins `homelab-net`; public HTTPS/login/CSS 200 with valid TLS. Orange Pi direct GitLab route remains 404. The static VPS address in the client secret is an external tunnel exception, not an internal datastore call. |
| OCR proxy -> Mac native OCR | LAN `10.10.0.6:8787` | VM100 task namespace `/capacity 200`; required outside-Docker exception |
| VPS Registry trial -> VM100 GitLab | VPS labels -> private server `:8086`; control `7003`; VM100 client -> `tasks.gitlab_gitlab:5005` | Trial OCI push/pull and local backup verified on 2026-09-16; old Pi5 registry remains production; lab split DNS/edge route blocks native lab pull cutover. |
| Edge LLM route -> Mac LM Studio | LAN `10.10.0.6:1234` | Active file route; `llm` remains in development, not changed |

The refreshed running Swarm/VM100 env scan (variable names only, no secret
values) found no Pi5 DB/Redis IP literals. Mac native OCR in OCR proxy and
`OPENCLAW_TRUSTED_PROXIES=10.10.0.2,172.30.0.0/16` are intentional. The
dynamic file's `10.10.0.0/24` entry is
another allow-list, not an upstream. Running BDS app/tunnel env contained
no `10.10.0.*` literal. No synthetic user OCR document, MyPocket action,
or NetBird enrollment was submitted to claim end-to-end flow coverage.

## Risk and design recommendation

The shared overlay makes raw `postgres:5432`, `redis-prod:6379`, and other
Pi5 backends reachable by any attached Swarm task. Redis password and DB
credentials still protect application data, but network access is wider
than each service needs. A future segmentation should preserve the
file-provider routing model and use multiple overlays:

1. `ingress-net`: Orange Pi Traefik plus only HTTP backends it routes;
   workers and raw datastores should not join it.
2. `data-net`: Pi5 PgBouncer/Redis and only their consuming VM100 tasks;
   direct `postgres:5432` access restricted to build/migration clients
   and GitLab while the session-mode pooler remains incompatible with GitLab.
3. App-specific networks where genuine private east-west traffic exists,
   e.g. MyPocket web/API/worker and NetBird server/dashboard. Keep
   `bds-tunnel-net` unchanged for app/cloudflared only.
4. Edge transport/DNS networks only if Rathole-to-Traefik and AdGuard
   published-port behavior are verified; do not remove these services
   from `homelab-net` based on membership alone.

This is a topology proposal, **not** a deployed network split. It needs
explicit design approval and one-service-at-a-time canaries, task namespace
DNS/auth probes, cross-route checks, and saved rollback specs. Fresh helpers
attached to Orange Pi `homelab-net` correlated with unresolved overlay ARP
in the long-lived Traefik task during earlier canaries, so diagnostics
should share the existing Traefik namespace. The exact Docker/kernel root
cause remains unproven.

## Operational follow-up

- Preserve LAN PgBouncer/Redis mappings for inventoried non-Docker clients;
  MyPocket API/worker no longer require them.
- Use the 1 GiB `noeviction` shared `redis-prod` for the approved GitLab plan;
  consider a dedicated instance if contention or key namespace issues arise.
- Public docs need no change for this audit: domains, API behavior, and
  user configuration did not change. This internal note records runtime
  membership and a future design option.
