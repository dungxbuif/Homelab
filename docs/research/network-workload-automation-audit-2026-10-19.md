---
type: Research
title: "Network, Workload and Automation Audit (2026-10-19)"
description: "Live audit of service networks, host workload placement, and a proposed automation model for the homelab and database tier"
timestamp: 2026-10-19T00:00:00+07:00
---

# Network, Workload and Automation Audit

Evidence: read-only SSH to Pi5, VM100 and the VPS on 2026-10-19, plus repository
docs. Proxmox host capacity, the Mac and the Orange Pi were **not** measured.

## 1. Host capacity and load

| Host | CPU / RAM | Disk | Observed | Role today |
|---|---|---|---|---|
| Pi5 `rpivn` | 4 / 7.9 GB (swap 4 GB) | 207/469 GB (46%) | 3.9 GB used; CouchDB 1.56 GB, Postgres 0.37 GB | Swarm manager, edge (Traefik, AdGuard, Rathole), Postgres+PgBouncer, CouchDB, Redis, RustFS, registry, pgAdmin, monitoring, Semaphore, provisioner |
| VM100 | 6 / 16 GB (swap 8 GB) | 149/194 GB (77%) | 5.5 GB used; GitLab 3.5 GB, OpenClaw 0.7 GB | All applications, GitLab, runners, RelayHub, NetBird, whiteboard, CouchLoom |
| VPS | 8 GB | 7.6/38 GB | 0.8 GB used | Public Traefik, Rathole server, NetBird relay, coturn |
| Orange Pi Zero 3 | n/a | n/a | Swarm node `Down` | Unused |

Findings:

- Pi5 concentrates every failure domain: edge, all datastores, the registry, the
  monitoring stack and the control plane (Semaphore). One host failure removes the
  network entry point, the databases and the tool used to recover them.
- VM100 has about 10 GB free RAM and 6 cores mostly idle; the constraint there is
  disk (77%), not compute.
- Data and tools that hold state are on a single NVMe (Pi5) with no SMART/wear
  monitoring.

## 2. Service networks

Swarm overlays: `homelab-net`, `edge-http-net`, `data-net`, `family-data-net`,
`mypocket-net`, `mypocket-redis-net`, `gitlab-net`, `knowledge-hub-net`,
`netbird-net`, `homelab-control-net`. Pi5 also carries seven legacy bridges
(`proxy_net`, `traefik_proxy`, `infra_proxy_net`, `infra_default`,
`dungxbuif_default`, `datcom_default`, `redis-prod_default`).

Findings:

1. `homelab-net` is still a flat shared network. Postgres, PgBouncer, CouchDB,
   RustFS, Redis, registry, pgAdmin, GitLab, OpenClaw, MyPocket, NetBird,
   RelayHub API and the tunnel clients all attach to it. Any compromised
   container can open a TCP connection to `postgres:5432`, `redis-prod:6379`
   and RustFS. Only passwords protect the data.
2. Segmentation has started but is not finished: `data-net`, `family-data-net`
   and `mypocket-redis-net` exist, yet `postgres` itself is still on
   `homelab-net`.
3. `openclaw` and `k8s-syntax` sit only on `homelab-net`; their real needs are
   undocumented.
4. Control plane: `homelab-control-net` is correctly limited to Traefik,
   provisioner, Semaphore and the runner. The provisioner also joins
   `homelab-net` and mounts `docker.sock` read-write.
5. Host-published datastore ports on Pi5: 5432 (PgBouncer), 16379 (Redis), 8428
   (VictoriaMetrics), 9093 (Alertmanager), all on `0.0.0.0`.
6. Legacy Pi5 bridges still carry live traffic (`proxy_net` hosts monitoring and
   several datastores). Retire them after moving those services to overlays.

### Target network model

| Network | Members | Purpose |
|---|---|---|
| `edge-http-net` | Traefik + HTTP apps | Only path from the edge to apps |
| `pg-net` | PgBouncer + consumers of the shared Postgres | Remove Postgres itself from `homelab-net` |
| `gitlab-db-net` | GitLab + its Postgres/Redis | GitLab keeps a direct DB path, isolated |
| `couch-net`, `s3-net`, `redis` nets | One consumer group each | Per-datastore reach |
| `control-net` | Traefik, provisioner, runner/CI executor | Automation only |
| `mon-net` | Exporters, VictoriaMetrics, Alertmanager | No host ports |

Rule: an app joins only the networks for datastores it uses. Drop `homelab-net`
after migration, bind the remaining host ports to the LAN address, and add host
firewall source lists for 5432 and 16379.

## 3. Workload distribution

Proposed tiers (hardware changes are options, not requirements):

| Tier | Where | Contents |
|---|---|---|
| Edge | Pi5 | Traefik, AdGuard, Rathole client. Add a standby (Orange Pi or a VM) with the same config |
| Data | Pi5 now; option: dedicated Proxmox VM | Postgres, PgBouncer, CouchDB, Redis, RustFS. Gains: vzdump snapshots, isolation from edge, room to grow |
| Apps | VM100 | All business apps and GitLab |
| Control and observability | Move to VM100 (or a small VM) | Semaphore (if kept), provisioner, VictoriaMetrics, Alertmanager, Grafana |

Why: a recovery tool must not live on the host it recovers. VM100 has spare RAM and
needs only disk cleanup; Pi5 loses its two heaviest non-data services.
Prerequisite: measure Proxmox spare CPU/RAM/disk before sizing a data VM.

## 4. Automation model

Current: systemd timers on VM100 run backups (works, independent of Semaphore);
Semaphore is a half-used second control plane (single replica, SQLite, most
templates are specs it never executes).

Proposed, using what already works:

1. **Git is the source of truth** (GitLab, existing). Stacks, Ansible roles and
   policies live in the repo.
2. **GitLab CI is the pipeline** (existing rootless runner): lint and secret scan,
   `docker compose config`/stack validation, Ansible `--check` as plan, then a
   protected-environment **manual approval** job that runs `docker stack deploy`
   through a forced-command SSH key. Approval is enforced by GitLab, which
   Semaphore Community cannot do.
3. **Nightly drift job**: compare `docker service ls` and published ports with
   the repo and report to Mezon.
4. **Image updates**: Renovate (or Diun in notify-only mode) with digest pinning;
   `update_config: order: start-first` and healthchecks for rollback.
5. **Break-glass**: documented workstation SSH path, because GitLab runs on the
   infrastructure it deploys.
6. Semaphore: keep only live read-only templates (host-audit, backup-health)
   until replaced; stop expanding it.

### Database server automation

- Provisioning stays declarative (existing provisioner and catalog), triggered
  from a CI job instead of a UI; roles are never `SUPERUSER`.
- Backup: keep the systemd + restic + Drive path. Add a dead-man's switch,
  a `configs` class, vzdump of VM100, automated monthly restore test. Add
  pgBackRest only if PITR is needed.
- Monitoring: postgres-exporter exists. Add alerts for replication/WAL age (if
  PITR), connections near limit, disk, backup staleness, NVMe wear/temperature.
- HA is not justified yet. First separate the failure domains (section 3).
- Use `pg_dump` per database before every major image or schema change.

## 5. Order of work

1. Segment Postgres/Redis networks and bind host ports (no new hardware).
2. Move monitoring and control plane off Pi5; add dead-man's switch.
3. Add GitLab CI deploy job with manual approval; start drift job.
4. Backup gaps (configs, VM100 vzdump, restore test).
5. Decide on a data VM after measuring Proxmox capacity.
