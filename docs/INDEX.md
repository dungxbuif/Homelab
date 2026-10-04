---
type: Dashboard
title: "Homelab Core Documentation Index"
description: "Centralized table of contents for Homelab core files, workloads, and services (v3.3 — Pi5 edge and Mac service tunnel)"
timestamp: 2026-09-16T00:00:00+07:00
---

# Homelab Core Infrastructure (v3.3)

* [Current Stack Catalog](./STACK.md) - current workloads, tunnel exceptions, DB endpoints, backup boundaries, and proposed work; Markdown for people and agents.
* [Documentation Audit](./research/docs-stack-audit-2026-09-16.md) - corrected drift and runtime verification coverage.
* [System Context & Playbook](./MAIN.md) — current VPS `gateway-traefik` -> Rathole -> Pi5 `edge-traefik-pi5` topology, Pi5 split DNS, service-export playbook, and bug registry.
* [Raspberry Pi 5 Datastore Spec](./PI.md) — Pi5 **active edge + manager/datastore node**: Traefik/Rathole/AdGuard, Postgres+PgBouncer, Redis-prod, RustFS, Registry, LibreSpeed, pgAdmin, and CouchDB.
* [VM100 Production Compute](./VM100.md) — production apps including MyPocket, n8n, OpenClaw, NetBird, RelayHub bootstrap and GitLab; portless Swarm plus isolated BDS Compose connector.
* [Mac Mini Runtime Dependencies](./MAC.md) — native OCR and LM Studio exposed through the Mac Rathole service tunnel; MyPocket dev checkout unmoved, production runtime on VM100; NetBird private admin access proposed.
* [MikroTik Router Hardening](./MIKROTIK.md) — PPPoE, local DHCP, WireGuard return-path routing, security hardening.
* [Proxmox Production Hypervisor](./PROXMOX.md) — VM100 production storage/lifecycle; optional practice VMs must be isolated from production and old K8s IaC.
* [Proxmox IaC Prerequisites](./PRE_REQUIRE.md) — Proxmox API tokens & SSH keys for Terraform/Ansible (generic; now used for lab VMs).
* [Network Diagnostic Trace](./CONTEXT.md) — benchmarks, bandwidth, latency, and DNS troubleshooting history.
* [CouchDB Obsidian Sync](./COUCHDB_OBSIDIAN_SYNC.md) — deployment, client settings, and recovery notes for the vault sync backend.
* [Local Project Workspace Inventory](./PROJECTS.md) — summary-only source checkout inventory; project folders live under `/Users/dungxbuif/workspace/`.
* [NetBird Deployment Note](./deployments/netbird-2026-09-13.md) — VM100 control plane, Pi5 PostgreSQL, VPS relay/STUN, deployed public allow-list, and pending LAN-routing peer enrollment.
* [n8n Daily Gold And Fuel Mezon Report](./deployments/n8n-daily-gold-fuel-report-2026-09-24.md) — 08:00 deterministic price report workflow, Mezon webhook config, sources, idempotency, and failure policy.
* [GitLab Runbook](./services/gitlab.md) - Omnibus components, Pi5 DB/Redis, public SSH and temporary VPS HTTPS; includes agent-readable facts.
* [GitLab Registry Trial](./deployments/gitlab-registry-trial-2026-09-16.md) - successful OCI smoke and local backup evidence; Pi5 registry still production.
* [Backup and Restore Runbook](./runbooks/backup-restore.md) - native CLI/API backup rules, post-check verification, Mezon status reporting, Google Drive retention, and restore boundaries.
* [Network Segmentation Proposal](./research/network-segmentation-2026-09-15.md) - broad shared overlay is deployed; narrower networks are not.
* [Resource Limit Audit](./research/resource-limit-audit-2026-09-15.md) - dated measurements and limits, not blanket approval to resize services.

# Standards & Guidelines

* [Open Knowledge Format (OKF) Specification](./OKF_SPEC.md) — the OKF v0.1 standard used across this bundle.

# Proposed Architecture

* [NetBird and Homelab Automation](./research/netbird-automation-feasibility-2026-09-13.md) - Research and proposed placement, private database access, Semaphore/Ansible workflows, and staged verification. Partially implemented by the VM100 bootstrap note above.

# Archived Legacy Documentation

* [Archived Index](./archived/INDEX.md) — retired K8s-era docs (cluster bootstrap, Longhorn, recovery, CI/CD, monitoring, OCR benchmarks, IaC design), preserved for historical reference.
