---
type: Audit
title: "Runtime Inventory and Deployment Reconciliation"
description: "Authoritative point-in-time inventory for the VPS, Pi5 edge/datastore, VM100 worker, Swarm services, Compose applications, image versions, and backup control plane"
timestamp: 2026-10-13T00:00:00+07:00
---

# Runtime Inventory and Deployment Reconciliation

**Observed:** 2026-10-13, through SSH and Docker/systemd read-only commands.
**Scope:** deployment and configuration reconciliation only. No service, route,
database, volume, or backup data was changed during this audit.

This is a historical baseline observed on 2026-10-13, not a perpetual source
of truth and not authority over live state. Preserve its original observations
below for comparison. As of 2026-10-15, use these newer bounded records:

- [Runtime/data reconciliation](runtime-catalog-reconciliation-2026-10-15.md)
- [Docker upgrade](vm100-docker-upgrade-2026-10-14.md)
- [Homepage release](homepage-automation-release-2026-10-15.md)
- [Route evidence](route-reconciliation-2026-10-15.md)
- [Resource audit](resource-audit-2026-10-15.md)
- [Application catalog corrections](app-catalog-reconciliation-2026-10-15.md)
- [Remote backup audit](backup-remote-audit-2026-10-15.md)

The active machine-readable inventory still declares incomplete coverage.
Neither this baseline nor those bounded updates prove full system acceptance.
The direct SSH commands below are historical audit examples, not the desired
operator workflow; use enrolled read-only Semaphore templates where available.

## Host Topology

| Host | Runtime | Current role | Version evidence |
|---|---|---|---|
| VPS `103.82.21.202` | Docker gateway | Public Traefik, shared Rathole, isolated GitLab tunnels, NetBird relay/STUN | Docker `29.3.0`; Traefik `v3.6`; Rathole server `rapiz1/rathole:latest`, image ID `sha256:a31b9178e985d4a84f46d4c3af6aa200ee0c5e7f821c7075a1f6669fb77392b1`; NetBird relay `netbirdio/relay:latest`, image ID `sha256:a845ba99641778b8e58df5abe5871ad374573f8b51c504691a5d7f406f477e93` |
| Pi5 `10.10.0.5` / `rpivn` | Docker Swarm manager, ARM64 | Active LAN/public edge, DNS, PostgreSQL/PgBouncer, Redis, RustFS, CouchDB, registry, Semaphore/provisioner | Docker Engine `28.4.0`; Linux `7.0.0-1020-raspi`; Swarm leader |
| VM100 `10.10.0.31` / `vm100-prod` | Docker Swarm worker plus Compose projects | Production application compute, GitLab, KubeKosh, CouchLoom; retired/absent BDS connector | Docker Engine `29.1.3`; Ubuntu 22.04; 6 vCPU, 16 GB RAM, 200 GiB disk, 8 GiB swap |
| Orange Pi `10.10.0.2` | Swarm node | Retired/unavailable edge node; must remain out of active routing | Swarm `Down`; old `edge_*` services are `0/0` |

The active edge is the Pi5 standalone trio. The old Swarm services named
`edge_traefik`, `edge_rathole`, and `edge_adguardhome` are intentionally scaled
to zero. VM100 is a worker, so `docker service ls` must be run on Pi5, not on
VM100; VM100's Compose projects are inspected with `docker compose`/container
inventory instead.

## Pi5 Current Runtime

### Active standalone edge and data containers

| Component | Image tag | Image ID / runtime note |
|---|---|---|
| `edge-traefik-pi5` | `traefik:v3.6` / OCI `v3.6.25` | `sha256:68269702cdcb1643b456923f45379722d65fca7d71cb85d4daf6bf6038fae376`; registry `v3.6.25` is already the running image; host `80/443`; file provider |
| `edge-rathole-pi5` | `rathole:local` | `sha256:0a1c8a87fc0eab6d23ffa1b55e5018d229e9968eb320a0e36e159d2aad68dea9`; local build, no registry semantic version |
| `edge-adguardhome-pi5` | `adguard/adguardhome:latest` / v0.107.79 | `sha256:e38d0ed0724eb284aa9e196359bd24cae4fff315b4550270cca948986b4b16b8`; registry pull was up to date; `53/tcp+udp`, HTTP/HTTPS admin |
| `cadvisor` | `gcr.io/cadvisor/cadvisor:v0.55.1@sha256:3de2bd52…` | healthy; `/metrics` reports cAdvisor `v0.55.1`; host metrics collector |
| PostgreSQL | `pgvector/pgvector:pg16@sha256:7b822b0a…` | PostgreSQL 16.15; raw DB remains internal, PgBouncer is the approved client endpoint; upgraded and verified 2026-10-31 |
| Redis production | `redis:7.2-alpine@sha256:2c933526…` | Redis 7.2.17; AOF enabled; shared logical DB policy is documented in `STACK.md`; upgraded and RDB-restored 2026-10-31 |
| RustFS | `rustfs/rustfs:1.0.4@sha256:ed9210d6…` | Production image upgraded and verified 2026-10-31; see [controlled upgrade ledger](./version-upgrade-2026-10-31.md). |
| CouchDB | `couchdb:3.5.3@sha256:bed314d1…` | Obsidian/LiveSync source of truth; upgraded and verified 2026-10-31 |
| Semaphore | `semaphoreui/semaphore:v2.19.17@sha256:008dacd9…` | healthy; UI/executor verified in the 2026-10-31 upgrade ledger |
| Provisioner | `homelab/provisioner:20261005` | `sha256:abe3fca933569bd9d43b568022c385f2316e63113b7d41ff8d7f602de491a1c5`; internal only |

Pi5 Swarm Engine is `28.4.0`. Current one-replica application services in the
same Swarm are listed below; the image tag is the deployment identifier and the
image ID is the observed local artifact identifier.

| Swarm service | Image tag | Replica state |
|---|---|---|
| `homepage` | `homelab/homepage:vm100-20261007-stirling` | `1/1` |
| `k8s-syntax` | `homelab/k8s-syntax:af8481e` | `1/1` |
| `macocr-proxy` | `homelab/macocr-proxy:scan-api-20261008` | `1/1` |
| `mypocket-api` | `registry.dungxbuif.com/mypocket-api:release-73c4c37` | `1/1` |
| `mypocket-web` | `registry.dungxbuif.com/mypocket-web:release-d5c6ba8c` | `1/1` |
| `mypocket-worker` | `registry.dungxbuif.com/mypocket-api:release-73c4c37` | `1/1` |
| `family-tree` | `oven/bun:1-slim` | `1/1` |
| `mezonhook` | `homelab/mezonhook:vm100-20260911` | `1/1` |
| `n8n` | `docker.n8n.io/n8nio/n8n:stable` | `1/1`; image ID `sha256:a8c95f75c6fdf65f5f2b7a7b354744eaa1c62bb911b5c00af6499c3f38e4cd32` |
| `netbird_netbird-server` | `netbirdio/netbird-server:latest` | `1/1`; image ID `sha256:3086534361a18573b85897383a0753a97b8c75d68dee9926fbd7eccab1f2fe89` |
| `netbird_netbird-dashboard` | `netbirdio/dashboard:latest` | `1/1`; image ID `sha256:fa2d8b02a81761e4d2a22df4041d13316b7635f1e93273eafeb53d4991e55b5a` |
| `openclaw` | `homelab/openclaw:vm100-20260912` | `1/1` |
| `gitlab_gitlab` | `gitlab/gitlab-ce:18.11.11-ce.0` | `1/1`; healthy |
| `gitlab-ssh-tunnel_client` | `rapiz1/rathole@sha256:a31b9178e985d4a84f46d4c3af6aa200ee0c5e7f821c7075a1f6669fb77392b1` | `1/1` |
| `gitlab-https-tunnel_client` | same Rathole digest | `1/1` |
| `gitlab-registry-trial_client` | same Rathole digest | `1/1` |
| `stirling-pdf` | `docker.stirlingpdf.com/stirlingtools/stirling-pdf:3.1.0` | `1/1`; image ID `sha256:b5b9e400c086e5334a4947a0d7cd589808f743f29267d7f41c18200cf4bc48b4` |
| `semaphore_semaphore` | `semaphoreui/semaphore:v2.19.12` | `1/1` |

The old Swarm edge services and the old RelayHub bootstrap service are `0/0`.
`vigorous_napier` (`alpine:3.22`, `1/1`) is an auxiliary container and is not
part of the production application catalog; investigate before removing it.

## VM100 Current Runtime

### Compose applications

| Project / component | Image tag | State and boundary |
|---|---|---|
| `prod` / RelayHub API + worker | `homelab/relayhub:prod-eee9e7c` | API, worker, NATS and Redis healthy; private `relayhub-net`; public API through Pi5 edge |
| `prod` / NATS | `nats:2.14.5-alpine` | private RelayHub network only; image ID `sha256:d4ac35882ac65aff236cd65b9d3fa4d24332c681e1a85f94eedccd3cdd65b1da` |
| `prod` / Redis | `redis:7.4-alpine@sha256:8da19c73…` | private RelayHub network only; active Swarm task and legacy Compose rollback path verified; no persistence by design |
| `couchloom` | `couchloom:8f7a8e0` | healthy; image ID `sha256:cdca747d4df568004cfb02ec7477a3e77d8c33d11333693d0468c9a9b5307085` |
| `couchloom-postgres` | `pgvector/pgvector:0.8.6-pg17-bookworm` | healthy; private CouchLoom data network |
| `couchloom-ollama` | `ollama/ollama:0.40.13@sha256:b2f0122c…` | healthy; CPU embedding runtime; `nomic-embed-text` retained |
| `kubekosh` | `zeborg/kubekosh:latest` | LAN-only, privileged learning lab; image ID `sha256:c623098b4cd4a7813a04e08d08ee14c6dff26f30f8ff5272a076ca07a03a2125` |
| `bds-app` | retired/absent | older image entry; current audit found no matching container or `/opt/apps/bds` source |
| `bds-cloudflared` | retired/absent | older VM100 connector entry; current audit found no container or `/opt/apps/bds` source. Pi5 native `cloudflared` is a separate systemd service |

### Additional Swarm tasks observed on VM100

The VM100 worker also hosts the Swarm tasks listed in the Pi5 catalog. Current
image IDs for the most recently changed local artifacts include:

| Image | Observed image ID |
|---|---|
| `homelab/homepage:vm100-20261007-stirling` | `sha256:c357a8dd6e27d07b6c51ffb9c90793e82617519370dffedf8a5ce7e46ea86c4f` |
| `homelab/macocr-proxy:scan-api-20261008` | `sha256:e6907a8247b61aec142fcce4197e58c812db0f850f05ce5fd7e7aa6f18d33225` |
| `registry.dungxbuif.com/mypocket-web:release-d5c6ba8c` | release tag observed on the active task; use the tag as the deployment version |
| `homelab/k8s-syntax:af8481e` | `sha256:9b4237eeb462d8172e8da33380ab13a61c8517897b8ea07102bffaedbf5c5fe6` |

The MyPocket API and worker currently use the API release tag shown in the
Pi5 catalog. The worker is active in the live inventory, so older notes calling
it a legacy `0/0` service are stale.

## Ingress and Network Boundaries

```text
Public client
  -> VPS gateway-traefik :80/:443
  -> shared Rathole :7000
  -> Pi5 edge-traefik-pi5
  -> Docker DNS on homelab-net
  -> VM100 Swarm task or Pi5 backend

GitLab HTTPS/Registry/SSH
  -> VPS isolated Rathole listeners :7002/:7003/:7001/:2222
  -> VM100 tunnel clients
  -> gitlab_gitlab

NetBird
  -> VPS netbird-relay TCP 443 + UDP 3478
  -> VM100 control plane via Pi5 edge

BDS (historical only; current audit found no live connector or app source)
```

Pi5 Traefik is file-provider driven. It does not infer routes from Swarm
labels. App containers should remain portless and use `tasks.<service>` or
Docker service DNS on the required overlay. The `homelab-net` overlay is still
shared for legacy compatibility; private app networks such as `relayhub-net`,
`bds-tunnel-net`, and CouchLoom's data network provide the narrower boundaries.

## Backup and Provisioning State

VM100 systemd timers are enabled and active as the scheduler. The last observed
class markers on Pi5 are:

| Class | Run | Snapshot ID |
|---|---|---|
| PostgreSQL + CouchDB | `databases-20261012-180003` | `3298c3eefda04ba9e2397d024f9b359fd11d819325c436059489580a2c400961` |
| RustFS | `rustfs-20261012-213004` | `7e511fa365144b6247e63120222000c20adea72796ddc0806653cd480a6c3b82` |
| GitLab | `gitlab-20261012-193002` | `0e4c88063586aece8b924c56422ee0272779bac7b5743cc517b7a858e18b0df3` |

The health timer is also enabled, but its last oneshot run exited 1 because it
ran before the database/RustFS markers were written and logged a unit start-time
parse warning. This is a health-check/reporting issue, not evidence that the
three later class snapshots failed. It remains an explicit follow-up before
calling the health gate clean.

During this audit the VM100 GitLab runner was found to have a stale Mezon
webhook secret: its 121-byte file differed from the 205-byte Pi5 secret used by
the database and RustFS executor. The correct secret was copied to VM100 with
mode `0640`, owner `root:ubuntu`, and matching SHA-256. A single warning-level
delivery probe then returned successfully; the next scheduled GitLab class is
the final confirmation for the normal success notification.

Semaphore is a live private control plane on Pi5 with one project, one
`db-provision` template, one user, and one access key. Its task history was
restored from the preserved SQLite snapshot and the survey labels/messages were
normalized on 2026-10-13. It creates a PostgreSQL or CouchDB database/user,
writes the generated credential to the approved secret boundary, smoke-tests
the owner, and enrolls the resource in the backup catalog.

## Reconciled Recent Deployments

The following recent changes were either undocumented or only represented by
stale “pending/pilot” text in older docs; they are now covered by this snapshot
and the linked records:

- Pi5 standalone edge recovery and Orange Pi retirement as the active route;
- VM100 backup timers, native GitLab backup, RustFS export, Drive snapshots, and
  class-specific success markers;
- Semaphore SQLite history recovery and human-readable provisioning metadata;
- current RelayHub `prod-eee9e7c`, CouchLoom `8f7a8e0`, Homepage Stirling image,
  K8s Syntax, OCR proxy, MyPocket release tags, and current GitLab `18.11.11`;
- current NetBird control-plane/relay placement and KubeKosh LAN-only boundary;
- exact image tags/IDs for the current runtime, including unpinned `latest` or
  `stable` tags that remain reproducibility risks.

## Verification Commands

Run these from the documented owner host before changing deployment docs:

```bash
ssh pi 'docker node ls; docker service ls'
ssh vm100 'docker compose ls; docker ps --format "{{.Names}}|{{.Image}}"'
ssh vm100 'systemctl list-timers --all "homelab-backup*"'
ssh gateway 'docker ps --format "{{.Names}}|{{.Image}}|{{.Ports}}"'
```

The inventory is a point-in-time record. Re-run the commands and append a new
dated inventory after any image update, route cutover, host-role change, or
backup control-plane change.
