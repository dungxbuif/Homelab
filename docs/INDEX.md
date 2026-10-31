---
type: Dashboard
title: "Homelab Documentation Map"
description: "Map of the current homelab docs: status, catalog, hosts, services, runbooks, evidence and plan"
timestamp: 2026-10-31T12:00:00+07:00
---

# Homelab Documentation Map

Read in this order: STATUS -> STACK -> host or service reference -> runbook.
Dated records below are the 2026-10-31 evidence; older history is in git.
Source code lives in `/home/dungxbuif/workspace/projects/` (code for
infrastructure in `homelab-ops`), never in this vault.

## Current state

- [STATUS.md](./STATUS.md) — one-page status and open gates.
- [STACK.md](./STACK.md) — hosts, workloads, network, datastores, backups.
- [BACKLOG.md](./BACKLOG.md) — open work only.
- [LOG.md](./LOG.md) — changelog of significant decisions.
- [PROJECTS.md](./PROJECTS.md) — local project checkout inventory.
- [MAIN.md](./MAIN.md) — ingress topology and service export playbook.

## Host references

- [PI.md](./PI.md) — Pi5 edge, Swarm manager and datastores.
- [VM100.md](./VM100.md) — production compute.
- [MAC.md](./MAC.md) — native OCR and LM Studio.
- [PROXMOX.md](./PROXMOX.md) — hypervisor for VM100 and VM110.
- [MIKROTIK.md](./MIKROTIK.md) — router (DHCP DNS needs urgent verification).
- [PRE_REQUIRE.md](./PRE_REQUIRE.md) — Proxmox API token prerequisites for IaC.

## Services

- [services/gitlab.md](./services/gitlab.md) — GitLab CE on VM100.
- [services/couchloom.md](./services/couchloom.md) — CouchLoom second-brain.
- [services/databasus.md](./services/databasus.md) — Databasus backup UI.
- [services/relayhub-internals.md](./services/relayhub-internals.md) — RelayHub internal architecture.
- [services/relayhub-product-docs.md](./services/relayhub-product-docs.md) — RelayHub public docs boundary.
- [COUCHDB_OBSIDIAN_SYNC.md](./COUCHDB_OBSIDIAN_SYNC.md) — CouchDB vault sync.

## Runbooks

- [backup-restore.md](./runbooks/backup-restore.md)
- [databasus-backup-operations.md](./runbooks/databasus-backup-operations.md)
- [db-provisioning.md](./runbooks/db-provisioning.md)
- [automation-operations.md](./runbooks/automation-operations.md)
- [gitlab-redis-network.md](./runbooks/gitlab-redis-network.md)
- [secret-rotation-and-history-purge.md](./runbooks/secret-rotation-and-history-purge.md)
- [vault-git-protection.md](./runbooks/vault-git-protection.md)

## Evidence (2026-10-31)

- [version-upgrade-2026-10-31.md](./deployments/version-upgrade-2026-10-31.md) — image upgrade ledger and rollback sources.
- [backup-repair-2026-10-31.md](./deployments/backup-repair-2026-10-31.md) — Drive remote repair and restore acceptance.
- [gitlab-redis-network-repair-2026-10-31.md](./deployments/gitlab-redis-network-repair-2026-10-31.md) — GitLab/Redis overlay repair.
- [vps-gateway-audit-2026-10-31.md](./deployments/vps-gateway-audit-2026-10-31.md) — VPS live audit.

## Plan

- [Lab-wide IaC automation rebuild](./superpowers/plans/2026-10-31-lab-iac-automation-rebuild.md) — the only forward plan (proposed).

## Conventions

- [OKF_SPEC.md](./OKF_SPEC.md) — frontmatter conventions used in this vault.
- Diagrams: [`assets/diagrams/`](./assets/diagrams/).
