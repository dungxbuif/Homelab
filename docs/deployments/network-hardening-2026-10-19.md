---
type: Reference
title: "Network Hardening Rollout (2026-10-19)"
description: "Live changes made on the VPS, Pi5 and VM100 during the 2026-10-19 audit, with verification and rollback"
timestamp: 2026-10-19T00:00:00+07:00
---

# Network Hardening Rollout, 2026-10-19

Findings and the target model are in
[network-workload-automation-audit-2026-10-19.md](../research/network-workload-automation-audit-2026-10-19.md).
This note records only what was changed on live hosts. Status is **in progress**.

## Completed

| Area | Change | Verification | Rollback |
|---|---|---|---|
| VPS ports | Legacy Rathole service ports 18087 (`mac-ocr`) and 18123 (`mac-llm`) blocked from the Internet with a `DOCKER-USER` DROP rule; persisted by `block-legacy-tunnel-ports.service` | Both ports closed from outside; no Traefik route referenced them; public sites unchanged | `iptables -D DOCKER-USER -p tcp -m multiport --dports 18087,18123 -m conntrack --ctstate NEW -j DROP`; disable the unit |
| Mac | Container `mac-service-tunnel` (only service `mac-llm`) removed with `docker compose down` in `~/dev-env/mac-service-tunnel`; files kept | LM Studio tunnel no longer connected | `docker compose up -d` in the same directory |
| VPS SSH | `/etc/ssh/sshd_config.d/00-hardening.conf`: `PermitRootLogin prohibit-password`, `PasswordAuthentication no`, `KbdInteractiveAuthentication no`, `MaxAuthTries 6`, `LoginGraceTime 20` | Fresh key session succeeded; password attempt returns `Permission denied (publickey)` | Delete the file and `systemctl reload ssh` |
| Workstation | `~/.ssh/config` host `gateway` uses the 1Password "Gateway" key with `IdentitiesOnly yes` (public key at `~/.ssh/gateway-1password.pub`) | `KEY_LOGIN_OK` on first try | Restore `~/.ssh/config.bak-<date>` |
| VPS coturn | `/root/coturn/docker-compose.yml`: added `--denied-peer-ip` for private/loopback/link-local/CGNAT ranges, `--no-multicast-peers`, `--no-tcp-relay`, `--user-quota=12`, `--total-quota=300` | Container up, 5349 TCP/UDP listening, sites unchanged | Restore `/root/firewall-backup/coturn-compose.*.yml`, `docker compose up -d` |
| Pi5 network | Created overlay `pg-net` (`10.0.30.0/24`); `postgres` and `pgbouncer` connected live; `pg_hba` already allows all addresses with scram | 56 DB connections unchanged; sites unchanged | `docker network disconnect pg-net <container>`; `docker network rm pg-net` |
| Network anchor | Swarm service `pg-net-anchor` (busybox, 16 MB) pinned to VM100 so overlays are visible to non-swarm compose there | `docker network inspect pg-net` works on VM100 | `docker service rm pg-net-anchor` |
| VM100 disk | `docker builder prune` and `docker image prune` (dangling only) | Disk 81% to 77%; 6 GB reclaimed | Not reversible; images rebuild |
| RelayHub | `relayhub-api` container had been stopped since about 2026-10-15; started with `docker start` | `/` and `/openapi.json` return 200; healthy | `docker stop relayhub-api` |
| Stirling PDF | Swarm update had been `paused` since 2026-10-06; `docker service update --force stirling-pdf` | `1/1`; public 200 | n/a |
| Whiteboard | `/opt/apps/whiteboard/docker-compose.prod.yml` gained `pg-net` on `db-migrate`, `backend`, `collab`; `backend` and `collab` recreated | Both healthy, site 200; DB still reached through `homelab-net` because DNS resolves `postgres` there first | Restore `docker-compose.prod.yml.bak-pgnet-*` and `up -d --no-deps backend collab` |
| Pi5 network | Created overlay `s3-net` (`10.0.31.0/24`); `rustfs` connected live; `pg-net-anchor` also joined to `s3-net` | VM100 sees `s3-net`; `dungxbuif.com` and whiteboard 200 | `docker network disconnect s3-net rustfs`; `docker service update --network-rm s3-net pg-net-anchor`; `docker network rm s3-net` |

### 2026-10-20: public/private exposure layers

Two exposure layers exist: the VPS `gateway-traefik` HostSNI allow-list (names
absent from it are not forwarded) and the Pi5 `edge-traefik-pi5` `lan-only`
`ipAllowList`. `automation/routes/catalog.yml` marks `pgadmin`, `couchdb`,
`sync-db`, `semaphore`, `kubekosh` as `exposure: lan`, but the hand-edited live
`~/edge/traefik/dynamic.yml` only applied `lan-only` to `semaphore` and
`kubekosh`. Measured from the Internet path (curl `--resolve` to the VPS IP):
`pgadmin` 302, `couchdb` 401, `sync-db` 401 (reachable); `semaphore` and
`kubekosh` 404 (not forwarded).

| Change | Result | Rollback |
|---|---|---|
| Pi5 `dynamic.yml`: `middlewares: [lan-only]` on router `pgadmin` (Traefik `watch: true`, no restart) | Internet path 403, LAN path 302; other sites unchanged | Restore `~/edge/traefik/dynamic.yml.bak-pgadmin-lan-*` |
| Pi5 `dynamic.yml`: split router `couchdb` into `couchdb` (`couchdb.dungxbuif.com`, `lan-only`) and `sync-db` (public, same service) | Internet path: `couchdb` 403, `sync-db` 401; LAN path: both 401 | Restore `~/edge/traefik/dynamic.yml.bak-couchdb-lan-*` |
| Pi5 `dynamic.yml`: router `sync-db` rule limited to `Path(/)`, `Path(/_session)`, `PathPrefix(/obsidian_vault)` | Internet path: those return 401 (auth) and CORS preflight 204; `/_utils`, `/_all_dbs`, `/_node`, `/_config` return 404; other sites 200 | Restore `~/edge/traefik/dynamic.yml.bak-syncdb-path-*` |

**Incident and rollback:** removing `pgadmin.dungxbuif.com` from the VPS
HostSNI rule in `/root/gateway/dynamic.yml` was followed within seconds by
failures on `dungxbuif.com`, `n8n`, `relayhub`, `sync-db` (curl 000) and 404 on
`netbird`; GitLab (separate tunnel) stayed up. The file differed from the known
good copy only by the removed token and parsed as valid YAML. Restoring the
backup (`/root/firewall-backup/dynamic.yml.20261020-000241`) recovered every site
within seconds. Outage was roughly 3 to 4 minutes. **Root cause not identified**;
the failing file is kept as `/root/firewall-backup/dynamic.yml.broken-attempt`.
Do not retry the VPS allow-list edit until it is reproduced on a copy or a
maintenance window with the Traefik log open. `pgadmin` stays on the VPS
allow-list but is blocked at the Pi5 layer.

Decision recorded: Obsidian LiveSync is used from outside the LAN, so
`sync-db.dungxbuif.com` must remain reachable from the Internet. Checked every database on 2026-10-20 (only `obsidian_vault` has remote traffic; `homelab` is admin-only and stays LAN-side, see the CouchDB runbook). Done (see table):
restricted it to the vault database path (block `/_utils`, `/_all_dbs`, `/_node`,
`/_config`) after checking the plugin's required paths, and make
`couchdb.dungxbuif.com` (admin name) LAN-only.

### 2026-10-20: DB consumers moved to pg-net

| Change | Result | Rollback |
|---|---|---|
| Pi5 `docker-compose.yml`: postgres gets alias `postgres-pg` on `pg-net`; pgbouncer joins `pg-net` and uses `DB_HOST=postgres-pg` (live: alias via `docker network connect --alias`, `pgbouncer.ini` host edited, HUP) | New pgbouncer-to-postgres connections come from `10.0.30.4`; old ones age out; sites 200 | Restore `docker-compose.yml.bak-pgnet-*`, set `host=postgres`, HUP |
| VM100 whiteboard: `db-migrate`, `backend`, `collab` drop `homelab-net`; `DATABASE_URL` host `postgres-pg`; `s3-net` added for `rustfs` | Connections from `10.0.30.13/14`; backend and collab healthy; site 200 | Restore `docker-compose.prod.yml.bak-nohomelab-*` and `.env.prod.bak-nohomelab-*`, `up -d --no-deps backend collab` |
| GitLab stack: `db_host = postgres-pg`, `pg-net` added (keeps `homelab-net` for `redis-prod`), new swarm config `gitlab_omnibus_pgnet_20261020204731` | 40 connections from `10.0.30.15`; web 200; restart took about 4 minutes | Restore `gitlab-omnibus.rb.bak-pgnet-*` and `gitlab-stack.yml.bak-pgnet-*`, `docker stack deploy` |

## Pending in this rollout

- N1 is complete: PostgreSQL was removed from `homelab-net` after all observed
  database clients were confirmed on `pg-net`; one idle legacy PgBouncer
  backend session was terminated and re-established through `10.0.30.4`.
  The source backup is
  `/ssd-data/infra/docker-compose.yml.bak-pg-detach-20261020-214540`.
- NetBird was then migrated one service at a time: `pg-net` was added and
  `homelab-net` removed from `netbird_netbird-server`. The new task converged
  on VM100, used the existing PgBouncer DSNs, and all six old NetBird client
  sockets on `172.30.0.91` disappeared. Root domain remained HTTP 200.
- macOCR was migrated next with `pg-net` and a new app-specific
  `macocr-redis-net`; `homelab-net` was removed from the service. OCR
  `/healthz` and `/docs/` returned 200, the old `172.30.0.92` PgBouncer
  sockets disappeared, and the Redis Compose override was persisted. Backup:
  `/ssd-data/infra/redis-prod/docker-compose.override.yml.bak-macocr-net-20261020-214931`.
- RelayHub API and worker were migrated from the Pi5 LAN database endpoint to
  `pgbouncer:6432` on `pg-net`. The API uses `edge-http-net` for the Pi5 edge;
  the worker stays on `relayhub-net` and `pg-net`. Both containers are healthy,
  public `/readyz` is 200, and PostgreSQL sees RelayHub through PgBouncer at
  `10.0.30.4`. Source compose and env backups are retained under
  `/opt/apps/relayhub/prod/`.
- PgBouncer host bind was narrowed from all interfaces to `10.10.0.5:5432`.
  The container was recreated after clearing stale `Created` metadata, without
  restarting Postgres. DB clients reconnected through the new PgBouncer address
  and RelayHub, GitLab, Whiteboard, n8n and OCR public checks returned 200.
- VictoriaMetrics host bind was narrowed to `10.10.0.5:8428`; the container was
  recreated without changing its data volume. The LAN `/health` and TSDB API
  probes returned 200, and the application route smoke checks remained healthy.
  Backup: `/ssd-data/infra/docker-compose.yml.bak-bind-victoriametrics-20261020-215518`.
- Redis host bind was narrowed to `10.10.0.5:16379`; the container remained up
  and the application route smoke checks remained healthy. The existing Redis
  authentication and data volume were preserved.
- Alertmanager host bind was narrowed to `10.10.0.5:9093`; `/-/healthy` and
  `/api/v2/status` returned 200 without changing its configuration volume.
  Backup: `/ssd-data/infra/docker-compose.yml.bak-bind-alertmanager-20261020-215607`.

N4 is complete: all four previously broad Pi5 listeners (`5432`, `16379`,
`8428`, `9093`) now bind only to the LAN address `10.10.0.5`. The next network
step is N5: remove remaining `homelab-net` memberships one application at a
time, beginning with the Redis consumers after a live membership audit. MyPocket
API and worker are the first completed N5 pair: both now use `data-net`,
`mypocket-net`, and `mypocket-redis-net`; the Redis Compose override persists
that network and the API route remains healthy.
- Whiteboard: remove `homelab-net` from `backend` (replace with `pg-net` and
  `s3-net`) and from `collab` and `db-migrate`, so the DB path really uses
  `pg-net`. Not applied yet; the compose edit was blocked by the permission
  classifier.
- Move GitLab (direct DB user, 38 connections) to `pg-net` via `gitlab.rb` and a
  service update.
- Move PgBouncer consumers (`macocr-proxy`, NetBird, n8n, MyPocket) to the
  network PgBouncer shares with them; `relayhub-api` reaches PgBouncer through
  the LAN host port `10.10.0.5:5432`, so that port stays until RelayHub joins an
  overlay.
- After all consumers moved: `docker network disconnect homelab-net postgres`,
  then bind the remaining host-published datastore ports.

## Prepared in git, not deployed

| Branch | Commit | Content | State |
|---|---|---|---|
| `codex/backup-deadman-configs` | `7422efe` | Optional dead-man's-switch pings in `run-class.sh` (`HEALTHCHECK_URL_FILE` / `HEALTHCHECK_URL_DIR`), and a `configs` backup class (`backup/scripts/run-configs-backup.py`, `backup/configs-sources.json`, timer unit) disabled and unscheduled by default | 9 new tests plus 3 existing contract tests pass locally; `test_instance_enrollment.py` and `test_scheduler_generation.py` not run here (PyYAML/Jinja2 missing); docker collection path only skipped. Traefik paths in `configs-sources.json` are unverified guesses. Not merged or deployed. Human deploy steps are in `automation/backup-runner/README.md` |

## Open incidents seen during the work

- VM100 rebooted cleanly at 14:40 and 16:29 UTC on 2026-10-19 via
  `systemd-logind` ("System is rebooting"); initiator unknown and not this
  rollout. Sites returned 502 for about 4 minutes, GitLab for a few more.
- Pi5 and VM100 both rebooted at about 14:40 UTC; a shared power or network
  event is suspected. No UPS is documented.

## Known unresolved security items (deferred by the owner)

The GitHub repository `dungxbuif/Homelab` is **public** and contains a Grafana
admin credential in `monitoring/SKILL.md` and K8s-era secrets under
`deprecated/selfhost-v1/` (first commit 2026-08-17). Rotation is scheduled as a
separate phase; until then treat these as exposed.
