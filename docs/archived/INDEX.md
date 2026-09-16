---
type: Dashboard
title: "Archived Legacy Documentation Index"
description: "Index of retired K8s-era Homelab documentation, preserved for historical reference after the v3 Mac mini consolidation"
timestamp: 2026-08-17T00:00:00Z
---

# 🗄️ Archived Legacy Documentation

These documents describe retired homelab implementations: the 3-node Proxmox
Kubernetes cluster and the short-lived Caddy-era Orange Pi edge. They are
preserved here for historical reference after the **v3 Mac mini consolidation
(2026-08)** and the **Traefik edge cutover (2026-09)**.

> [!IMPORTANT]
> Nothing in this directory describes a live system. Do not follow these
> runbooks for current operations. For the current architecture see
> [../MAIN.md](../MAIN.md), [../VM100.md](../VM100.md),
> [../MAC.md](../MAC.md), and [../PI.md](../PI.md).

## K8s cluster & workloads (`k8s-v2/`)

* [k8s/INDEX.md](./k8s-v2/k8s/INDEX.md) — Kubernetes workloads directory index.
* [k8s/OMNISCAN.md](./k8s-v2/k8s/OMNISCAN.md) — retired Omniscan bot specification; no current production runtime.
* [k8s/MACOCR.md](./k8s-v2/k8s/MACOCR.md) — MacOCR platform spec, multi-arch build, HPA autoscaling (now on Mac; AI agent disabled).
* [k8s/CICD.md](./k8s-v2/k8s/CICD.md) — Portless GitOps model and autoscaling runner stack (GitLab CI + K8s runners).
* [k8s/DB.md](./k8s-v2/k8s/DB.md) — Database provisioning, replication, and stateful storage specs.
* [k8s/DB_INVENTORY.md](./k8s-v2/k8s/DB_INVENTORY.md) — historical database/schema catalog, not a current DB inventory; use the current stack/Pi5 runbooks.
* [k8s/LONGHORN_CONFIG_REVIEW.md](./k8s-v2/k8s/LONGHORN_CONFIG_REVIEW.md) — Longhorn storage architecture & volume replication review.
* [k8s/RECOVERY_GUIDE.md](./k8s-v2/k8s/RECOVERY_GUIDE.md) — Cluster recovery runbook (control plane, Longhorn, DBs).
* [k8s/goclaw.md](./k8s-v2/k8s/goclaw.md) — historical GoClaw architecture; GoClaw production runtime/route retired, distinct from OpenClaw.
* [k8s/migration_plan.md](./k8s-v2/k8s/migration_plan.md) — The earlier reverse-direction plan (Pi5 → K8s), superseded.
* [k8s/migration_k8s_to_mac.md](./k8s-v2/k8s/migration_k8s_to_mac.md) — **The v2→v3 migration record** (K8s → Mac mini). This is the bridge document that explains how the homelab got to v3.

## IaC & cluster design

* [2026-05-29_k8s_proxmox_iac_design.md](./k8s-v2/2026-05-29_k8s_proxmox_iac_design.md) — Original design spec: provisioning VMs and bootstrapping HA Kubernetes on Proxmox via Terraform/Ansible.
* [PROXMOX.k8s.md](./k8s-v2/PROXMOX.k8s.md) — retired cluster guide. Use [current Proxmox](../PROXMOX.md) for production VM100; do not destroy reused VM IDs from old state.
* [goclaw_implementation_plan.md](./k8s-v2/goclaw_implementation_plan.md) — GoClaw deployment & hardening plan (transition doc; GoClaw ended up on Pi5 Docker).

## Observability & benchmarks

* [monitoring/README.md](./k8s-v2/monitoring/README.md) — Observability specs & ChatOps (Prometheus/Grafana stack on K8s; Grafana retired 2026-08).
* [monitoring/INDEX.md](./k8s-v2/monitoring/INDEX.md) — Monitoring index.
* k8s-v2 also holds the **OCR benchmark reports** (`BENCHMARK_REPORT.md`,
  `BATCH_BENCHMARK_REPORT.md`) — performance studies run against the K8s HPA
  proxy just before the migration. Useful as a baseline if re-benchmarking the
  single-Mac-proxy OCR path.

## Caddy-era Orange Pi edge (`edge-caddy-era/`)

* [migration_orange_pi_edge.md](./edge-caddy-era/migration_orange_pi_edge.md) — superseded Pi5/Orange Pi Caddy migration plan. Do not execute; current edge deploys Traefik.
* [rathole.toml.orange-pi](./edge-caddy-era/rathole.toml.orange-pi) — old Rathole client example that targeted Caddy.
* [attach-pi5-to-overlay.sh](./edge-caddy-era/attach-pi5-to-overlay.sh) — old overlay attachment helper for Caddy-era backend discovery.
* [edit-adguard-for-orange-pi.sh](./edge-caddy-era/edit-adguard-for-orange-pi.sh) — old AdGuard cutover helper from the Caddy migration.

## Superseded active plans (`superseded-plans/`)

* [2026-09-07-access-platform-migration.md](./superseded-plans/2026-09-07-access-platform-migration.md) — unexecuted access-platform migration plan with Caddy/Mac-era assumptions. It is retained for context only; reconcile it against current VM100 + Orange Pi Traefik topology before reusing any idea.

## Superseded Topology Snapshots (`superseded-topology/`)

* [Old entry point](./superseded-topology/index-before-docs-audit-20260916.md) - preserved before removing stale VM100 host ports and MyPocket/AWS-only placement claims.
* [Old system playbook](./superseded-topology/main-before-docs-audit-20260916.md) - original diagram, inherited WireGuard record and policy text before 2026-09-16 reconciliation.
* [Old Proxmox AWS-only guide](./superseded-topology/proxmox-aws-only-before-20260916.md) - superseded by production VM100 hypervisor runbook.

## Related legacy code/config (not in this folder)

* `deprecated/selfhost-v1/` (repo root) — the v1 Pi5 selfhost stack, pre-K8s.
* `deprecated/goclaw-k8s/` (repo root) — the abandoned GoClaw-on-K8s manifests.
* `iac/terraform/` - historical K8s provisioning state/config. Reconcile and
  back it up before reuse; VM100 is production and may reuse an old state ID.
