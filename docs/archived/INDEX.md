---
type: Dashboard
title: "Archived Legacy Documentation Index"
description: "Index of retired K8s-era Homelab documentation, preserved for historical reference after the v3 Mac mini consolidation"
timestamp: 2026-08-17T00:00:00Z
---

# 🗄️ Archived Legacy Documentation

These documents describe the **retired** 3-node Proxmox Kubernetes cluster and
its workloads. They are preserved here for historical reference after the
**v3 Mac mini consolidation (2026-08)**, when all user-facing workloads were
migrated off the K8s cluster onto the Mac mini and the cluster was retired.

> [!IMPORTANT]
> Nothing in this directory describes a live system. Do not follow these
> runbooks for current operations. For the current architecture see
> [../MAIN.md](../MAIN.md), [../MAC.md](../MAC.md), and [../PI.md](../PI.md).

## K8s cluster & workloads (`k8s-v2/`)

* [k8s/INDEX.md](./k8s-v2/k8s/INDEX.md) — Kubernetes workloads directory index.
* [k8s/OMNISCAN.md](./k8s-v2/k8s/OMNISCAN.md) — Omniscan bot platform spec & operations (now on Mac; see ../../MAC.md).
* [k8s/MACOCR.md](./k8s-v2/k8s/MACOCR.md) — MacOCR platform spec, multi-arch build, HPA autoscaling (now on Mac; AI agent disabled).
* [k8s/CICD.md](./k8s-v2/k8s/CICD.md) — Portless GitOps model and autoscaling runner stack (GitLab CI + K8s runners).
* [k8s/DB.md](./k8s-v2/k8s/DB.md) — Database provisioning, replication, and stateful storage specs.
* [k8s/DB_INVENTORY.md](./k8s-v2/k8s/DB_INVENTORY.md) — Database/schema catalog (the DB list is still accurate; DBs remain on Pi5).
* [k8s/LONGHORN_CONFIG_REVIEW.md](./k8s-v2/k8s/LONGHORN_CONFIG_REVIEW.md) — Longhorn storage architecture & volume replication review.
* [k8s/RECOVERY_GUIDE.md](./k8s-v2/k8s/RECOVERY_GUIDE.md) — Cluster recovery runbook (control plane, Longhorn, DBs).
* [k8s/goclaw.md](./k8s-v2/k8s/goclaw.md) — GoClaw architecture & resource bounds (GoClaw now runs on Pi5 Docker).
* [k8s/migration_plan.md](./k8s-v2/k8s/migration_plan.md) — The earlier reverse-direction plan (Pi5 → K8s), superseded.
* [k8s/migration_k8s_to_mac.md](./k8s-v2/k8s/migration_k8s_to_mac.md) — **The v2→v3 migration record** (K8s → Mac mini). This is the bridge document that explains how the homelab got to v3.

## IaC & cluster design

* [2026-05-29_k8s_proxmox_iac_design.md](./k8s-v2/2026-05-29_k8s_proxmox_iac_design.md) — Original design spec: provisioning VMs and bootstrapping HA Kubernetes on Proxmox via Terraform/Ansible.
* [PROXMOX.k8s.md](./k8s-v2/PROXMOX.k8s.md) — The previous Proxmox guide (K8s cluster storage, VM resources, kubeadm + kube-vip). Replaced by [../PROXMOX.md](../PROXMOX.md) (AWS lab).
* [goclaw_implementation_plan.md](./k8s-v2/goclaw_implementation_plan.md) — GoClaw deployment & hardening plan (transition doc; GoClaw ended up on Pi5 Docker).

## Observability & benchmarks

* [monitoring/README.md](./k8s-v2/monitoring/README.md) — Observability specs & ChatOps (Prometheus/Grafana stack on K8s; Grafana retired 2026-08).
* [monitoring/INDEX.md](./k8s-v2/monitoring/INDEX.md) — Monitoring index.
* k8s-v2 also holds the **OCR benchmark reports** (`BENCHMARK_REPORT.md`,
  `BATCH_BENCHMARK_REPORT.md`) — performance studies run against the K8s HPA
  proxy just before the migration. Useful as a baseline if re-benchmarking the
  single-Mac-proxy OCR path.

## Related legacy code/config (not in this folder)

* `deprecated/selfhost-v1/` (repo root) — the v1 Pi5 selfhost stack, pre-K8s.
* `deprecated/goclaw-k8s/` (repo root) — the abandoned GoClaw-on-K8s manifests.
* `iac/terraform/` — still holds the K8s cluster (`k8s-cp-1/2/3`)
  `terraform.tfstate` until the cluster VMs are destroyed; back it up before
  reusing the workspace for the AWS lab.
