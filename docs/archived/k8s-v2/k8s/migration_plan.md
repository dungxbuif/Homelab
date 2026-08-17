# 🚀 Homelab Migration Plan: Centralized DBs, Kestra, and Pi 5 Simplification

This document details the plan to migrate your services from the Raspberry Pi 5 into the Proxmox-based Kubernetes cluster, centralize all databases, set up Kestra for automated backups, and reduce the Pi 5 footprint.

## ⚠️ User Review Required & Open Questions

Before we begin execution, please review the following architectural decisions and open questions. 

> [!WARNING]
> **Rathole, Caddy, & AdGuardHome Migration**: You mentioned keeping *only* `goclaw`, `VictoriaMetrics`, and `cAdvisor` on the Pi 5. Currently, `rathole` handles the tunnel from your VPS (Traefik) to the Pi, and `caddy` acts as the ingress on the Pi. 
> * **Question 1**: Should `rathole` and `caddy` (or an equivalent K8s Ingress Controller like Nginx/Traefik) be moved to K8s? If so, we need to adjust the VPS Traefik routing to tunnel directly into the K8s cluster (or have Rathole in K8s connect out to the VPS).
> * **Question 2**: Should `adguardhome` (DNS) also move to K8s, or does it stay on the Pi?

> [!IMPORTANT]
> **Database Data Migration Strategy**: We will need some downtime to migrate data from the Pi 5 databases to the new K8s databases to prevent data inconsistency. 
> * **Question 3**: Are you okay with temporary downtime for services like `n8n` and `gitlab` while we perform `pg_dump`/`pg_restore` and CouchDB data sync?

> [!TIP]
> **Google Drive Credentials for Kestra**: To allow Kestra to backup databases to Google Drive, you will need to provide a Google Cloud Service Account JSON key later during the Kestra configuration phase.

---

## 🛠️ Phase 1: Centralized Database Deployment (K8s)

Following the architecture defined in `docs/k8s/DB.md`, we will consolidate all persistent databases into a single Kubernetes namespace.

### Kubernetes Manifests

#### [NEW] `k8s/database/namespace.yml`
Creates the `database` namespace.

#### [NEW] `k8s/database/postgres/` (PostgreSQL Stack)
- `statefulset.yml`: Deploy PostgreSQL (using `pgvector:pg16` to match your current setup) with a Longhorn PVC.
- `service.yml`: ClusterIP service (`postgres.database.svc.cluster.local`).
- `secret.yml`: Database credentials for `homelab` db and `admin` user.
- `pgbouncer.yml`: Migrate PgBouncer for connection pooling to K8s.

#### [NEW] `k8s/database/couchdb/` (CouchDB Stack)
- `statefulset.yml`: Deploy CouchDB with a Longhorn PVC.
- `service.yml`: ClusterIP service.
- `configmap.yml`: local.d configurations.

#### [NEW] `k8s/database/network-policy.yml`
- Cilium Network Policies to explicitly restrict ingress traffic to the DBs, ensuring only authorized namespaces (e.g., `prod` where n8n lives) can access them.

### Data Migration
- Exec into the Pi 5 `postgres` container, dump all databases (`pg_dumpall`).
- Restore the dump into the new K8s PostgreSQL instance.
- Rsync or replicate CouchDB data from the Pi to the K8s CouchDB Persistent Volume.

---

## 🔄 Phase 2: Kestra Installation & Backup Workflows

We will install Kestra, a modern scheduling and orchestration platform, to handle automated database backups.

### Kubernetes Manifests

#### [NEW] `k8s/kestra/`
- Deploy Kestra via its official Helm chart or Kustomize manifests.
- Connect Kestra's backend to the new centralized PostgreSQL instance in the `database` namespace.

### Kestra Flows

#### [NEW] Kestra Backup Flows (Defined as Code)
- **Postgres Backup Flow**: Scheduled daily. Uses a Docker task to run `pg_dump`, compresses the output, and uploads it to Google Drive using the `io.kestra.plugin.gcp.gdrive.Upload` task.
- **CouchDB Backup Flow**: Scheduled daily. Dumps CouchDB data/config and uploads to Google Drive.

---

## 🚀 Phase 3: Service Migration (Pi 5 -> K8s)

We will systematically migrate the remaining docker-compose services from the Pi 5 to Kubernetes.

### Target Services to Migrate
For each of the following, we will create K8s Deployment/StatefulSet, Service, Ingress, and Longhorn PVC manifests:
1. **n8n**: Connects to the new K8s PostgreSQL.
2. **GitLab**: Needs careful volume migration for config, logs, and data (`/var/opt/gitlab`).
3. **RustDesk Server (`rustfs`)**: Needs PVC for its data directory.
4. **pgAdmin**: Connects to the K8s PostgreSQL.
5. **Docker Registry**: Needs PVC for `/var/lib/registry`.
6. **LibreSpeed (`speedtest`)**: Stateless, simple deployment.

---

## 🧹 Phase 4: Pi 5 Simplification

Once all services are verified running on K8s and data is confirmed intact, we will clean up the Pi 5.

### Actions on Pi 5
#### [MODIFY] `/ssd-data/infra/docker-compose.yml`
- We will completely strip down the docker-compose file.
- **Keep**:
  - `goclaw`
  - `victoriametrics`
  - `cadvisor`
  - `node-exporter` (Highly recommended to keep this for monitoring the Pi's own OS metrics)
- **Remove**: All other services (Postgres, n8n, GitLab, etc.).

---

## ✅ Verification Plan

### Database & Storage
- Check Longhorn UI to ensure all PVCs for Postgres, CouchDB, GitLab, etc., are created and healthy.
- Connect to the new K8s Postgres instance and verify all tables/data exist.

### Kestra Backups
- Manually trigger the Kestra backup flows.
- Verify that the compressed backup files appear correctly in your Google Drive.

### Application Routing
- Ensure all services (n8n, GitLab) are reachable via their designated local/public domains.
- Verify network policies correctly allow n8n to talk to Postgres, but block unauthorized pods.

### Pi 5 Load
- Check `htop` or Grafana to verify the Pi 5 resource usage has significantly dropped, confirming the workload successfully shifted to Proxmox K8s.
