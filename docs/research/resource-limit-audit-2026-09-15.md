# Pi5 and VM100 resource-limit audit (2026-09-15)

## Intent and baseline before Redis change

The operator requested a shared Redis cap increase, then a whole-service
resource-limit audit with increase/decrease recommendations for Pi5 and
VM100. This note records the planned config change and verification before
implementation; measured per-service findings will be reconciled afterwards.

Pi5 has 7.7 GiB RAM total, about 3.8 GiB used and 4.0 GiB available, with
no swap. Current container sample: CouchDB ~1.62 GiB and ~26% CPU,
Postgres ~293 MiB under a 2 GiB container limit, RustFS ~382 MiB,
pgAdmin ~318 MiB, and `redis-prod` ~3.5 MiB RSS. Authenticated Redis INFO
reported ~988 KiB used, `maxmemory` 256 MiB, `allkeys-lru`, AOF enabled,
zero evictions/rejected connections/error replies and no keys in the INFO
keyspace snapshot. This is a point-in-time sample, not a peak.

## Pi5 swap decision (before implementation)

The operator requested swap during this resource pass. Pi5 root is
NVMe-backed ext4 `/dev/nvme0n1p2` with 334 GiB free; no swap is active.
Create a 4 GiB `/ssd-data/infra/swapfile` with mode 0600 on this filesystem,
initialize it with `mkswap`, and enable it through a small systemd service
(`migration/pi5-swap.service`) rather than editing the existing fstab.
Persist `vm.swappiness=10` in a sysctl drop-in. Verify `swapon --show`,
`free -h`, service enabled/active, exact file mode/size, and root disk
headroom. Swap is a last-resort OOM buffer; sustained swapping or memory
pressure still calls for service tuning or more physical RAM.

## Redis decision and verification plan

The operator selected one Redis instance shared with GitLab, OCR, and
MyPocket. Keep the same `redis-prod` image, password, AOF/data bind, default
bridge plus `homelab-net` alias, and LAN `16379` mapping. Raise
`maxmemory` from 256 MiB to **1 GiB** and change `maxmemory-policy` from
`allkeys-lru` to **`noeviction`**: GitLab Sidekiq queues/shared state must
not be silently evicted. Pi5 available RAM is sufficient for this cap on
the current sample, but no swap and CouchDB's larger footprint justify
measuring again after GitLab. At the cap, writes should fail visibly;
monitor `used_memory`, `evicted_keys`, `total_error_replies`, container RSS,
and Pi5 available memory. A dedicated GitLab Redis remains the fallback if
shared-instance contention or key namespace risk appears.

Before change: save the current Compose file outside git, inspect merged
config with password redacted, and record Redis auth/AOF/mount/network/URL
client baselines. Apply only command flags for memory/policy through a
structured YAML edit, verify parsed Compose parity, then recreate only
`redis-prod`. After change: authenticated `PING`, Redis INFO, same bind/
networks, OCR DB/Redis/native/public probes, MyPocket task health, and Pi5
RAM sample. Rollback only the Compose flags from backup and recreate Redis
without clearing AOF/data if clients regress.

## Executed Redis and swap changes

Pi5 `homelab-pi5-swap.service` is enabled and active. The swapfile is
4 GiB, mode 0600, with `vm.swappiness=10`; `swapon --show` and `free -h`
showed 4 GiB active and 0 used. The Redis Compose file was backed up on Pi5
before a structured YAML edit. Only `redis-prod` was recreated. Authenticated
`PING` returned `PONG`; INFO reported `maxmemory_human:1.00G`,
`maxmemory_policy:noeviction`, AOF enabled, and loading complete. Password,
data bind, LAN port, bridge network, and `homelab-net` alias were preserved.
OCR and MyPocket tasks stayed healthy; the OCR, money, and Family public routes
returned 200. Pi5 available RAM was about 4.0 GiB; swap remained unused.
This verifies the change at idle load, not under future GitLab load.

## Audit method after change

Inventory actual Docker/Swarm CPU and memory limits/reservations, restart
policies, current RSS/CPU, OOM/restart counts, and host free RAM/disk for
**every running Pi5 and VM100 service**. Distinguish configured limits from
observed usage; one snapshot cannot prove peaks. Identify over-tight caps,
missing upper bounds for noisy neighbors, and needless over-allocation.
Recommend values conservatively and apply no broad resource changes until
per-service impact is reviewed and monitored under GitLab workload.

## Live inventory after MyPocket migration

At 2026-09-15 15:39 UTC, Pi5 had 7.7 GiB RAM, 3.8 GiB used, 4.0 GiB
available, 4 GiB swap unused, and 329 GiB disk free. VM100 had 15 GiB RAM,
1.5 GiB used, 13 GiB available, no swap, and 137 GiB root disk free.
Before GitLab, all 15 Swarm services had **zero CPU/memory limits and reservations** in
their specs. All inspected running containers reported zero restarts and
`OOMKilled=false`; this does not prove they never restarted historically.
Pi5 PostgreSQL is the sole container with a hard limit (2 GiB memory,
1.5 CPUs); other running standalone containers had no Docker memory/CPU cap.
Redis has a 1 GiB logical `maxmemory`, distinct from a Docker RSS cap.
Values below are one `docker stats --no-stream` sample.

| Pi5 container | RSS / CPU | Current bound | Recommendation |
|---|---:|---|---|
| `redis-prod` | 4.9 MiB / 0.15% | Redis 1 GiB; no Docker cap | Keep; watch RSS/AOF overhead under GitLab load; consider ~1.5 GiB Docker cap after peak measurement |
| RelayHub test worker | 8.0 MiB / 0.10% | None | Keep isolated bridge; confirm test stack need |
| RelayHub test API | 8.2 MiB / 0% | None; host `:8080` | Confirm developer usage, then remove bind or stop test stack |
| RelayHub test PostgreSQL | 36.8 MiB / 0.07% | None | Test-only, not production PostgreSQL |
| RelayHub test NATS | 9.5 MiB / 1.68% | None | Test-only; no public route |
| `rustfs` | 389 MiB / 0.15% | None | Observe S3 peak before a 1-2 GiB cap |
| `blackbox-exporter` | 30 MiB / 0% | None | Candidate 128-256 MiB cap after scrape validation |
| `node-exporter` | 21 MiB / 0% | None | Candidate 128-256 MiB cap; no host bind |
| `snmp-exporter` | 34 MiB / 0% | None | Candidate 128-256 MiB cap after scrape validation |
| `alertmanager` | 21 MiB / 0.07% | None; host `:9093` | Audit LAN clients/firewall before changing bind; candidate 256 MiB cap |
| `victoriametrics` | 143 MiB / 0.22% | None; host `:8428` | Review retention/disk growth; candidate 1 GiB cap after peak measurement |
| `cadvisor` | 80 MiB / 2.01% | None | Candidate 256-512 MiB cap after scrape validation |
| `postgres-exporter` | 25 MiB / 0.18% | None | Candidate 128-256 MiB cap after scrape validation |
| `registry` | 23 MiB / 0.02% | None | Keep; watch push/load before cap |
| `couchdb` | 1.64 GiB / 0.35% | None | Largest Pi5 neighbor; inspect cache/peak, then consider 2.5-3 GiB cap |
| `postgres` | 267 MiB / 0.10% | 2 GiB, 1.5 CPU | Keep cap; inspect connections/peaks after GitLab |
| `pgbouncer` | 6.1 MiB / 0.05% | None; host `:5432` | Keep LAN exception; candidate 256 MiB cap after pool stress test |
| `pgadmin` | 319 MiB / 0.09% | None | Candidate 768 MiB-1 GiB cap; review admin access separately |
| `librespeed` | 17 MiB / 0% | None | Candidate 256 MiB cap |

| VM100 container/service | RSS / CPU | Current bound | Recommendation |
|---|---:|---|---|
| `openclaw` | 580 MiB / 0.81% | None | Candidate 1.5-2 GiB cap after model/plugin peak measurement |
| `mypocket-worker` | 2.6 MiB / 0% | None | Candidate 256-512 MiB cap after job peak measurement |
| `mypocket-api` | 2.9 MiB / 0% | None | Candidate 256-512 MiB cap after request peak measurement |
| `mypocket-web` | 6.0 MiB / 0% | None | Candidate 256 MiB cap |
| `family-tree` | 96 MiB / 0.27% | None | Candidate 512 MiB-1 GiB cap after Bun/upload peak measurement |
| `relayhub` bootstrap | 1.7 MiB / 0% | None | Candidate 256 MiB cap; expected `/readyz 503` is not OOM |
| `mezonhook` | 6.7 MiB / 0% | None | Candidate 256 MiB cap |
| `homepage` | 6.8 MiB / 0% | None | Candidate 256 MiB cap |
| `macocr-proxy` | 16 MiB / 0.17% | None | Candidate 512 MiB cap after upload peak measurement |
| NetBird dashboard | 36 MiB / 0.01% | None | Candidate 512 MiB cap |
| `n8n` | 426 MiB / 0.60% | None | Candidate 1.5-2 GiB cap after workflow peak measurement |
| NetBird server | 28 MiB / 0% | None | Candidate 1 GiB cap after enrollment/relay peak measurement |
| `bds-cloudflared` | 18 MiB / 0.24% | None | Candidate 256 MiB cap; preserve tunnel-only bridge |
| `bds-app` | 103 MiB / 0% | None | Candidate 1 GiB runtime cap after separating build peaks |

No sampled container is near a configured hard limit. CPU did not show
sustained saturation in this snapshot. More Pi5 RAM or VM100 CPU is not
justified solely by idle usage; GitLab load is the next real capacity test.
Apply proposed caps one service at a time only after peak telemetry and
rollback specs are available.

## GitLab startup capacity sample

After GitLab CE 18.11.11 became healthy on VM100, it used about 3.05 GiB
inside its 10 GiB cap and ~44% CPU in one snapshot. GitLab is the 16th
Swarm service and the only one with Swarm resources configured: 10 GiB/4
CPU limit and 2 GiB/1 CPU reservation. VM100 root rose from
58 to 64 GiB used, leaving 131 GiB free; internal login returned 200 and
SSH banner was reachable via Docker DNS. Pi5 PostgreSQL rose to about
492 MiB within its 2 GiB cap. GitLab held 37 connections (36 idle) and
the shared server had 60/100 connections total; watch for sustained
80+ before increasing `max_connections` with a planned PostgreSQL restart.
Redis used 2.54 MiB logical memory under the 1 GiB `noeviction` cap;
GitLab DB2 had 631 keys. Pi5 still had about 4.0 GiB available RAM,
but swap used 134 MiB after migration. Five `vmstat` samples showed
`si=0` and `so=0`, so there was no observed ongoing swap churn. Recheck
connections/RAM/swap after real users and CI jobs; this sample does not
justify increasing Pi5 or VM100 allocation immediately.

Public docs do not need an update for this internal resource-policy change:
domains, app APIs, and user configuration remain unchanged.

## GitLab SSH tunnel envelope

The isolated VM100 `gitlab-ssh-tunnel_client` is now the 17th Swarm service.
It has a 128 MiB/0.5 CPU limit and 32 MiB/0.1 CPU reservation; one idle
sample used 3.246 MiB and 0.00% CPU. The separate VPS Compose
`gitlab-ssh-rathole-server` has a 128 MiB/0.5 CPU cap, log rotation at
10 MiB x 3 files, and used 3.16 MiB/0.00% CPU in one sample. Both caps
have ample idle headroom; remeasure under sustained Git clones rather than
lowering them based on idle usage. The VPS server's two published TCP ports
are Git SSH `2222` and the authenticated Noise client channel `7001`; it
does not consume VM100 overlay addresses or Pi5 datastore memory.

## Temporary GitLab HTTPS tunnel envelope (2026-09-16)

The portless VM100 `gitlab-https-tunnel_client` is the 18th Swarm service.
It has a 128 MiB/0.5 CPU limit and 32 MiB/0.1 CPU reservation; one idle
sample used 5.531 MiB/0.00% CPU. The isolated VPS Compose
`gitlab-https-rathole-server` has a 128 MiB/0.5 CPU cap, 10 MiB x 3 log
rotation, and used 5.668 MiB/0.00% CPU in the same sample. Only the
authenticated Noise channel `7002/tcp` is host-published; HTTP `8085/tcp`
is private to VPS Docker `gateway-network`. VM100 still had about 10 GiB
available RAM and 131 GiB free on its 194 GiB root filesystem. The idle
sample supports keeping these limits, not reducing them or extrapolating
capacity under sustained Git-over-HTTPS use.
