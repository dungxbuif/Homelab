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

## Execution baseline before segmentation (2026-09-16)

The first execution pass for
[app private network and load audit](../superpowers/plans/2026-09-16-app-private-network-and-load-audit.md)
was read-only. No Swarm network, service, container, or route was changed.

VM100 was reachable through direct SSH as `ubuntu@10.10.0.31` with the
homelab key. Docker reported `Swarm=active` and `Control=false`, confirming
VM100 is a worker and cannot run `docker service ls` or `docker service
update`. A manager session is required before creating overlay networks or
migrating services.

Running VM100 container membership:

| Container / service task | Networks |
|---|---|
| `bds-app` | `bds-tunnel-net`, `homelab-net` |
| `bds-cloudflared` | `bds-tunnel-net` |
| `family-tree` | `homelab-net` |
| `gitlab_gitlab` | `homelab-net` |
| `gitlab-https-tunnel_client` | `homelab-net` |
| `gitlab-registry-trial_client` | `homelab-net` |
| `gitlab-ssh-tunnel_client` | `homelab-net` |
| `homepage` | `homelab-net` |
| `macocr-proxy` | `homelab-net` |
| `mezonhook` | `homelab-net` |
| `mypocket-api` | `homelab-net` |
| `mypocket-web` | `homelab-net` |
| `mypocket-worker` | `homelab-net` |
| `n8n` | `homelab-net` |
| `netbird_netbird-dashboard` | `homelab-net` |
| `netbird_netbird-server` | `homelab-net` |
| `openclaw` | `homelab-net` |
| `relayhub` | `homelab-net` |

BDS connector isolation remains correct: `bds-cloudflared` is only on
`bds-tunnel-net`. All observed VM100 Swarm service tasks are still on the
broad `homelab-net`, which is exactly the segmentation work remaining.

SSH access blockers:

| Host | Result |
|---|---|
| Pi5 manager alias `pi` | `Permission denied (publickey,password)` |
| Orange Pi alias `orange-pi` | timeout during SSH banner exchange |
| VPS alias `gateway` | `Permission denied (publickey,password)` |

Public route smoke from the Mac side succeeded before any changes:

| URL | Result |
|---|---|
| `https://dungxbuif.com/` | 200 |
| `https://family.dungxbuif.com/` | 200 |
| `https://mezonhook.dungxbuif.com/` | 200 |
| `https://n8n.dungxbuif.com/healthz` | 200 |
| `https://openclaw.dungxbuif.com/` | 200 |
| `https://money.dungxbuif.com/` | 200 |
| `https://gitlab.dungxbuif.com/users/sign_in` | 200 |
| `https://registry-gitlab.dungxbuif.com/v2/` | 401 |

Next action: restore or provide working manager access to Pi5 before Task 2
can create the target overlay networks. Do not promote VM100 to manager just
to bypass SSH unless that is a deliberate cluster-management decision.

## Emergency edge fallback during first segmentation attempt (2026-09-16)

Attempting to attach `edge-http-net` to `edge_traefik` caused the Orange Pi
Traefik task to enter `Accepted`/`Pending` instead of `Running`. The service
spec was rolled back to only `homelab-net`, but the Orange Pi node then
reported `Down` from the Swarm manager. SSH to `10.10.0.2` returned no route
or host down, so Orange could not be repaired in place.

To restore public traffic while leaving the Orange node untouched, temporary
standalone containers were started on VM100:

| Temporary container | Host | Purpose |
|---|---|---|
| `traefik-temp` | VM100 | Binds host `80/tcp`, `443/tcp`, and `443/udp`; joins `homelab-net`; uses the same Traefik static/dynamic config copied from this repo and `acme.json` extracted from the Pi5 edge backup archive. |
| `rathole-temp` | VM100 | Host-network Rathole client using the Orange/Pi5 edge client config snapshot; connects to VPS control `103.82.21.202:7000` and forwards public HTTP/HTTPS to VM100 localhost. |

Public smoke through the VM100 fallback returned 200 for homepage, Family
Tree, MezonHook, n8n healthz, OpenClaw, MyPocket, and GitLab sign-in; GitLab
Registry trial returned the expected 401 challenge.

This fallback is intentionally temporary. When Orange Pi is reachable again:

1. Confirm Orange Docker/Swarm is healthy and `edge_traefik` can run `1/1`.
2. Stop VM100 `rathole-temp` first so the VPS shared tunnel returns to Orange.
3. Verify public routes through Orange.
4. Stop VM100 `traefik-temp` and remove `/home/ubuntu/edge-temp*` only after
   Orange edge has been stable.

Do not continue app network segmentation while the edge is in fallback mode.

## App-by-app canary attachment while edge fallback is active (2026-09-16)

The operator asked to continue app by app while Orange Pi remained down. The
safe interpretation was to **attach** narrower networks and verify each app,
but not remove `homelab-net` yet. Removing the shared network is deferred
until Orange Pi edge is healthy again and Traefik can be verified from the
normal edge node.

Created/confirmed attachable Swarm overlays:

| Network | Purpose |
|---|---|
| `edge-http-net` | Future narrowed Traefik-to-HTTP-backend network |
| `data-net` | Future narrowed PgBouncer/Redis data access network |
| `mypocket-net` | MyPocket private app network |
| `netbird-net` | NetBird private app network |
| `gitlab-net` | GitLab/tunnel private app network |

Pi5 data containers attached to `data-net` while preserving existing
memberships:

| Container | Networks after change |
|---|---|
| `pgbouncer` | `data-net`, `homelab-net`, `proxy_net` |
| `redis-prod` | `data-net`, `homelab-net`, `redis-prod_default` |

VM100 Swarm services were migrated one at a time by adding new networks
only. All still retain `homelab-net` as rollback/compatibility while the
edge runs through VM100 fallback:

| Service | Added networks | Verification |
|---|---|---|
| `homepage` | `edge-http-net` | `https://dungxbuif.com/` 200 |
| `family-tree` | `edge-http-net` | `https://family.dungxbuif.com/` 200 |
| `mezonhook` | `edge-http-net` | `https://mezonhook.dungxbuif.com/` 200 |
| `mypocket-web`, `mypocket-api`, `mypocket-worker` | `mypocket-net`, `data-net` | API/web healthy; `https://money.dungxbuif.com/` 200; API resolves `pgbouncer` and `redis-prod` |
| `n8n` | `edge-http-net`, `data-net` | container healthy; `https://n8n.dungxbuif.com/healthz` 200 |
| `openclaw` | `edge-http-net` | container healthy; `https://openclaw.dungxbuif.com/` 200 |
| `macocr-proxy` | `edge-http-net` | container healthy; `https://ocr.dungxbuif.com/healthz` 200 |
| `relayhub` | `edge-http-net` | `https://relayhub.dungxbuif.com/healthz` 200 |
| `netbird_netbird-server`, `netbird_netbird-dashboard` | `netbird-net`, `edge-http-net` | `https://netbird.dungxbuif.com/` 200 |
| `gitlab_gitlab`, `gitlab-ssh-tunnel_client`, `gitlab-https-tunnel_client`, `gitlab-registry-trial_client` | `gitlab-net` | GitLab warmed up after restart; sign-in 200; Registry trial 401 |

Observed caveats:

- Each service restart caused a short health-starting window; public routes
  briefly returned 502 until the new task became healthy.
- GitLab took about a minute to boot Puma/Rails. During that window, tunnel
  clients could not resolve or connect to `tasks.gitlab_gitlab`; this cleared
  after GitLab finished network attachment and app boot.
- `macocr-proxy` is healthy, but logs show the native Mac OCR endpoint
  `10.10.0.6:8787` returning connection refused. That is an existing native
  dependency issue, not caused by the overlay attachment.
- `homelab-net` removal remains deliberately **not done**. The next cut must
  happen after Orange Pi returns or after a deliberate decision to make VM100
  the permanent edge.

Full public smoke after the canary attachments returned 200 for homepage,
Family Tree, MezonHook, n8n, OpenClaw, MyPocket, OCR healthz, RelayHub
healthz, NetBird dashboard, and GitLab sign-in; GitLab Registry trial
returned the expected 401 challenge.
