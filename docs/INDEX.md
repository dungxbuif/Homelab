---
type: Dashboard
title: "Homelab Core Documentation Index"
description: "Centralized table of contents for Homelab core files, workloads, and services (v3 — Mac-centric production)"
timestamp: 2026-08-17T00:00:00Z
---

# Homelab Core Infrastructure (v3)

* [System Context & Playbook](./MAIN.md) — v3 topology (Mac mini production + Orange Pi edge + VPS boundary + Proxmox AWS lab), Caddy/Rathole/AdGuard on Orange Pi, Docker Swarm overlay to Pi5 datastores, service-export playbook, and bug registry.
* [Raspberry Pi 5 Datastore Spec](./PI.md) — Pi5 **datastore & persistent services**: Postgres+PgBouncer, Redis-prod, RustFS, Registry, n8n, LibreSpeed, pgAdmin, CouchDB, GitLab, GoClaw, monitoring stack, Docker Swarm manager.
* [Mac Mini Production Stack](./MAC.md) — homepage / macocr-proxy / omniscan-bot; native OCR bridge; build-time AI-agent disable; operations runbook pointer.
* [MikroTik Router Hardening](./MIKROTIK.md) — PPPoE, local DHCP, WireGuard return-path routing, security hardening.
* [Proxmox Guide (AWS Lab Repurpose)](./PROXMOX.md) — Proxmox repurposed as a self-hosted AWS practice lab (LocalStack / eksctl / k3s); K8s cluster retired.
* [Proxmox IaC Prerequisites](./PRE_REQUIRE.md) — Proxmox API tokens & SSH keys for Terraform/Ansible (generic; now used for lab VMs).
* [Network Diagnostic Trace](./CONTEXT.md) — benchmarks, bandwidth, latency, and DNS troubleshooting history.
* [CouchDB Obsidian Sync](./COUCHDB_OBSIDIAN_SYNC.md) — deployment, client settings, and recovery notes for the vault sync backend.

# Standards & Guidelines

* [Open Knowledge Format (OKF) Specification](./OKF_SPEC.md) — the OKF v0.1 standard used across this bundle.

# Archived Legacy Documentation

* [Archived Index](./archived/INDEX.md) — retired K8s-era docs (cluster bootstrap, Longhorn, recovery, CI/CD, monitoring, OCR benchmarks, IaC design), preserved for historical reference.
