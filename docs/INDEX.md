---
type: Dashboard
title: "Homelab Core Documentation Index"
description: "Centralized table of contents for Homelab core files, workloads, and services (v3.4 — Pi5 edge, VM100 production worker, and Mac service tunnel)"
timestamp: 2026-10-17T00:00:00+07:00
---

# Homelab Core Infrastructure (v3.5)

* [Runtime Inventory and Deployment Reconciliation](./deployments/runtime-inventory-2026-10-13.md) — historical 2026-10-13 baseline; use the later 2026-10-15/16 reconciliation notes for current runtime state.
* [Backup Hardening Plan, 2026-10-20](./deployments/backup-hardening-plan-2026-10-20.md) — phased plan: disk, schedule and health, dead-man's switch, restore drill, config backup.
* [Homelab Backlog](./BACKLOG.md) — consolidated open work (security, network, backup, exposure, automation) with the 2026-10-20 backup assessment.
* [Network Hardening Rollout, 2026-10-19](./deployments/network-hardening-2026-10-19.md) — live changes, verification, rollback, and pending steps; paired with the [network, workload and automation audit](./research/network-workload-automation-audit-2026-10-19.md).
* [Current Stack Catalog](./STACK.md) - current workloads, tunnel exceptions, DB endpoints, backup boundaries, and proposed work; Markdown for people and agents.
* [Documentation Audit](./research/docs-stack-audit-2026-09-16.md) - corrected drift and runtime verification coverage.
* [System Context & Playbook](./MAIN.md) — current VPS `gateway-traefik` -> Rathole -> Pi5 `edge-traefik-pi5` topology, Pi5 split DNS, service-export playbook, and bug registry.
* [Raspberry Pi 5 Datastore Spec](./PI.md) — Pi5 **active edge + manager/datastore node**: Traefik/Rathole/AdGuard, Postgres+PgBouncer, Redis-prod, RustFS, Registry, LibreSpeed, pgAdmin, and CouchDB.
* [VM100 Production Compute](./VM100.md) — production apps including MyPocket, n8n, OpenClaw, NetBird, RelayHub bootstrap and GitLab; portless Swarm plus isolated BDS Compose connector.
* [Mac Mini Runtime Dependencies](./MAC.md) — native OCR connects outbound over WSS; only LM Studio remains on the Mac Rathole tunnel; includes the installed app and manual artifact locations.
* [MacOCR Outbound Worker Release](./deployments/macocr-outbound-2026-10-06.md) — production image, Universal app artifacts, admin routes, verification, account cleanup, and rollback boundary.
* [MyPocket API-only Runtime](./deployments/mypocket-api-only-2026-10-13.md) — production web shutdown, direct API route, service state, verification and rollback.
* [MikroTik Router Hardening](./MIKROTIK.md) — PPPoE, local DHCP, WireGuard return-path routing, security hardening.
* [Proxmox Production Hypervisor](./PROXMOX.md) — VM100 production storage/lifecycle; no Kubernetes VM or cluster is active, and any future practice VM must be isolated from production.
* [VM100 OpenTofu import module](../automation/tofu/proxmox/README.md) — import-only boundary for VM ID 100 with destroy protection and no historical K8s targets.
* [Proxmox IaC Prerequisites](./PRE_REQUIRE.md) — Proxmox API tokens & SSH keys for Terraform/Ansible (generic; now used for lab VMs).
* [Network Diagnostic Trace](./CONTEXT.md) — benchmarks, bandwidth, latency, and DNS troubleshooting history.
* [CouchDB Obsidian Sync](./COUCHDB_OBSIDIAN_SYNC.md) — deployment, client settings, and recovery notes for the vault sync backend.
* [Local Project Workspace Inventory](./PROJECTS.md) — summary-only source checkout inventory; project folders live under `/Users/dungxbuif/workspace/`.
* [NetBird Deployment Note](./deployments/netbird-2026-09-13.md) — VM100 control plane, Pi5 PostgreSQL, VPS relay/STUN, deployed public allow-list, and pending LAN-routing peer enrollment.
* [n8n Daily Gold And Fuel Mezon Report](./deployments/n8n-daily-gold-fuel-report-2026-09-24.md) — 08:00 deterministic price report workflow, Mezon webhook config, sources, idempotency, and failure policy.
* [GitLab Runbook](./services/gitlab.md) - Omnibus components, Pi5 DB/Redis, public SSH and temporary VPS HTTPS; includes agent-readable facts.
* [GitLab Registry Trial](./deployments/gitlab-registry-trial-2026-09-16.md) - successful OCI smoke and local backup evidence; Pi5 registry still production.
* [Backup and Restore Runbook](./runbooks/backup-restore.md) - native CLI/API backup rules, post-check verification, Mezon status reporting, Google Drive retention, and restore boundaries.
* [Database Provisioning Runbook](./runbooks/db-provisioning.md) - validated database/user creation contract, secret boundary, and staging workflow.
* [Backup Runner](../automation/backup-runner/README.md) - serial export/upload/post-check flow, retention lock, and schedule contract.
* [Native Backup Pull Transport](./deployments/backup-native-pull-transport-2026-10-21.md) - private-network PostgreSQL/RustFS transport and staged CouchDB proxy boundary.
* [CouchDB Backup Proxy](./deployments/couchdb-backup-proxy-2026-10-21.md) - GET-only VM100-to-Pi5 proxy, credential boundary, restore evidence, and current cutover gate.
* [RustFS Native Pull Cutover](./deployments/rustfs-native-pull-cutover-2026-10-21.md) - production S3 network, read-only key, export and restore evidence.
* [VM100 Vzdump Preflight](./deployments/vm100-vzdump-preflight-2026-10-21.md) - current Proxmox capacity and the separate-failure-domain requirement.
* [GitLab CI Homepage Approval](./deployments/gitlab-ci-homepage-approval-2026-10-21.md) - manual release contract and live enrollment gate.
* [Backup Control-Plane Plan](./superpowers/plans/2026-10-04-homelab-backup-control-plane.md) - historical design record for the now-active Ansible/backup architecture.
* [Homelab Automation Control Plane Plan](./superpowers/plans/2026-10-13-homelab-automation-control-plane.md) - staged plan for Semaphore, Ansible, OpenTofu, private execution, route generation, app deployment, drift audit, and removal of direct agent-to-host operations.
* [Semaphore Control Plane](./deployments/semaphore-backup-ui-2026-10-04.md) - private Pi5 UI/provisioner deployment, route, secret boundary, verification, and rollback; current metadata recovery is recorded in the runtime inventory.
* [Semaphore History and Metadata Recovery](./deployments/semaphore-recovery-2026-10-13.md) - restored task history, operator-facing fields, and current provisioning contract.
* [Network Segmentation Proposal](./research/network-segmentation-2026-09-15.md) - selected narrower overlays are active; the rollout is not yet complete.
* [Resource Limit Audit](./research/resource-limit-audit-2026-09-15.md) - dated measurements and limits, not blanket approval to resize services.

# Standards & Guidelines

* [Open Knowledge Format (OKF) Specification](./OKF_SPEC.md) — the OKF v0.1 standard used across this bundle.

# Proposed Architecture

* [NetBird and Homelab Automation](./research/netbird-automation-feasibility-2026-09-13.md) - Research and proposed placement, private database access, Semaphore/Ansible workflows, and staged verification. Partially implemented by the VM100 bootstrap note above.

# Archived Legacy Documentation

* [Archived Index](./archived/INDEX.md) — retired K8s-era docs (cluster bootstrap, Longhorn, recovery, CI/CD, monitoring, OCR benchmarks, IaC design), preserved for historical reference.
