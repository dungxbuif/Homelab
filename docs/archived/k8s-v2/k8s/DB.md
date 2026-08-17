---
type: Reference
title: "PostgreSQL & Redis DB Workloads Setup"
description: "Database workloads specification, container setup, volume mappings, and cluster configs"
timestamp: 2026-07-03T15:14:00Z
---

# 🗄️ Centralized Database Architecture

To optimize resource utilization and simplify lifecycle management across the homelab cluster, we have decided to centralize all persistent databases.

## ⚙️ Design Decision & Trade-offs

- **Centralized Namespace**: A dedicated namespace called `database` will host all persistent databases (PostgreSQL, MySQL, Redis, etc.) instead of running isolated databases within individual application namespaces.
- **Resource Efficiency**: Consolidating database workloads reduces idle CPU/RAM overhead, saving approximately `1GB - 1.5GB` of RAM across our Proxmox-based HA cluster.
- **Management Simplicity**: Simplifies backup schedules, persistent volume claim (PVC) management, monitoring, and database clustering/replication setups.
- **Centralized PostgreSQL (2026-06-06)**: All PostgreSQL databases in the lab (including services running on the K8s cluster) are centrally hosted on the Raspberry Pi 5. Internal communication is routed through the domain `postgres.dungxbuif.com`.


---

## ⚠️ Risks & Mitigation Strategies

While this architecture is optimal for resource-constrained Homelab environments, it introduces specific architectural challenges that must be mitigated:

### 1. Increased Blast Radius (Single Point of Failure)
- **Risk**: If the centralized database service or the underlying storage controller (e.g., Longhorn) encounters an outage, *all* dependent services (n8n, whiteboard, etc.) will experience service disruption simultaneously.
- **Mitigation**: Deploy critical database engines (like PostgreSQL) in a High-Availability stateful configuration (e.g., using patroni/replica nodes or native clustering) and ensure robust scheduled backups to external storage (S3/MinIO) are set up.

### 2. Network Isolation & Cross-Namespace Access
- **Risk**: Applications running in other namespaces need to connect across namespace boundaries (connecting to `<service-name>.database.svc.cluster.local`). This bypasses standard single-namespace isolation.
- **Mitigation**: Leverage **Cilium Network Policies** to explicitly restrict access to database ports. Only permit authorized application pods (e.g., n8n pods in the `prod` namespace) to establish TCP connections to the specific database instance ports in the `database` namespace.

### 3. Resource Contention (Noisy Neighbors)
- **Risk**: A resource-intensive query or batch job in one application (e.g., heavy automated workflows in n8n) can saturate the database CPU/RAM, degrading performance for all other applications.
- **Mitigation**: Strictly define Kubernetes CPU/Memory `requests` and `limits` on database workloads to prevent them from resource-starving nodes, and create distinct database instances/users within the engine to limit session pools.

---

## 📂 Database Inventory

*Detailed deployment logs, specs, and connection guides will be maintained here as we deploy individual engines.*