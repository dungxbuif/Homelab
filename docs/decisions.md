---
type: Decision Record
title: Standing Decisions
description: Architectural decisions and constraints still in force for the homelab
generated:
  by: claude-code/opus-5.5
  at: "2026-10-31T16:00:00+07:00"
stale_after: 2027-01-31 00:00:00+07:00
tags:
- decisions
- architecture
---

# Standing Decisions

Standing architectural decisions and constraints carried forward from earlier
entries. Current architecture marker: **v3.4** — Pi5 Swarm manager and active
edge, VM100 production worker, VM110 db-ops worker, Semaphore provisioning
control plane. The Proxmox K8s cluster (v2) is retired.

- **Topology:** one Swarm cluster managed from Pi5 `rpivn`. VM100 and VM110
  join it as workers; do not create a separate Swarm. Swarm service specs can
  only be changed from the Pi5 manager. `orangepizero3` is down but still a
  member and must not be treated as the edge.
- **Public boundary:** the VPS is the public boundary only (Traefik HostSNI
  allow-list, Rathole server, NetBird relay). Public traffic reaches the lab
  over Rathole to the Pi5 edge (`edge-traefik-pi5`, `edge-rathole-pi5`). GitLab
  HTTP uses its own isolated Rathole tunnel with TLS terminated on the VPS.
- **Data exposure:** pgAdmin/CouchDB host access is LAN-only on Pi5;
  `sync-db` is the only public CouchDB name and is path-restricted to the
  vault database. Semaphore is LAN/NetBird-only.
- **Provisioning (changing in plan P1):** Semaphore has no Docker socket; `homelab-provisioner` is
  the only Docker API holder, has no published port, and accepts only the
  Swarm token secret. Production deploys go through protected/manual jobs. Target: GitLab CI + `db_provision` replace Semaphore and the provisioner ([process](/docs/standards/database-provisioning.md)).
- **Network isolation:** BDS `cloudflared` stays only on `bds-tunnel-net` and
  must not join `homelab-net`. Datastore access uses Docker DNS names, not IP
  literals; GitLab reaches Redis via the `gitlab-net` overlay alias
  `redis-prod`.
- **Pi5 memory policy:** 4 GiB NVMe swap with swappiness 10; Redis 1 GiB
  logical memory with `noeviction` and AOF kept.
- **Secrets:** never in docs or commits. Runtime secrets live in ignored
  `local_vars.json`, service `.env` files on the host, or the password manager;
  webhook URLs (Mezon) are runtime secrets. Never embed a credential in a Git
  remote URL.
- **Backups:** every backup class must verify manifest, completion marker,
  checksums and remote snapshot before reporting; a backup counts only after a
  real restore check. Databasus is the database backup path with
  after-backup restore verification for approved service DBs.
- **Resource limits:** measured canaries are required before applying new
  Docker/Swarm CPU/memory caps; logging policy for Swarm services is audited
  from the manager.
- **Image updates:** Diun runs notify-only; upgrades follow the per-service
  ledger (backup, smoke test, rollback) in
  [version-upgrade-2026-10-31](/docs/deployments/version-upgrade-2026-10-31.md).
- **Source code:** project checkouts live under `/workspace/projects`, never
  in the vault; LiveSync covers `docs/**` only.
- **Forward plan:** the only roadmap is
  [Lab IaC and automation rebuild](./superpowers/plans/2026-10-31-lab-iac-automation-rebuild.md)
  (proposed).

Older history (entries before 2026-10-31) is available in git history of this
file.
