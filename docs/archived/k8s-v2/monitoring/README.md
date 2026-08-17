---
type: Reference
title: "Observability Stack Specifications"
description: "Infrastructure configurations of the Prometheus/Grafana stack, alerting matrices, and ChatOps webhook channels"
timestamp: 2026-07-03T15:14:00Z
---

# 📊 Homelab Monitoring & Observability Architecture

This document defines in detail the core metrics required to comprehensively monitor network resources and hardware parameters across all hosts in the Homelab. Based on these metrics, we architect the most optimal observability solution.

---

## 1. Core Metrics Definitions

To establish a unified, single pane of glass for system health, metrics are categorized into three primary layers: **Network**, **Host/Hardware**, and **Application/Cluster**.

### A. Network Metrics
This group focuses on detecting network bottlenecks, VPN disconnects, cable faults, or DNS resolution failures.

*   **Gateway / Router (MikroTik hEX S)**
    *   `wan_bandwidth_rx_tx`: Real-time Download/Upload bandwidth on the WAN interface (Mbps).
    *   `lan_bandwidth_rx_tx`: Traffic throughput across internal LAN ports.
    *   `active_connections_count`: Number of concurrent NAT connections (avoids NAT table exhaustion).
    *   `router_cpu_load`: CPU utilization of the router (crucial since MikroTik can experience CPU bottlenecks during high-speed NAT operations).
*   **Tunnel / Ingress (Rathole VPS & Caddy)**
    *   `tunnel_latency_ms`: Ping latency from the local LAN (Pi 5) to the Cloud VPS (monitors international routing stability).
    *   `ingress_http_requests_total`: Total number of HTTP requests processed by Caddy Ingress.
    *   `ingress_http_errors`: Number of HTTP 5xx errors (detects backend service outages).
*   **DNS Resolution (AdGuard Home)**
    *   `dns_queries_total`: Total number of DNS queries.
    *   `dns_blocked_total`: Number of queries blocked (adware, trackers, malware).
    *   `dns_upstream_latency_ms`: Response latency when querying upstream resolvers (e.g., Cloudflare `1.1.1.1`).
*   **Kubernetes Networking (Cilium eBPF)**
    *   `cilium_drop_count`: Number of packets dropped by NetworkPolicies (critical for security audit).
    *   `pod_to_pod_latency`: Network response time between microservices (e.g., `n8n` to `postgres`).

### B. Host & Hardware Metrics
Includes monitoring for `Raspberry Pi 5`, `Proxmox Host`, and `VMs (k8s-cp-1,2,3, worker)`.

*   **Compute**
    *   `node_cpu_utilization_percent`: CPU usage percentage.
    *   `node_load1`, `node_load5`: Operating system load averages.
    *   `node_hwmon_temp_celsius`: **CPU Temperature** (critical for Raspberry Pi 5 to prevent thermal throttling).
*   **Memory**
    *   `node_memory_MemAvailable_bytes`: Real available memory capacity (crucial since Pi 5 is constrained to 8GB RAM).
    *   `node_memory_Swap_used_bytes`: Warning indicator for swap usage (flags severe memory pressure).
*   **Storage**
    *   `node_filesystem_avail_bytes`: Alert trigger for low disk space (> 85% full).
    *   `node_disk_io_time_seconds_total`: Detects I/O bottlenecks on the external SSD (`/ssd-data`) of the Pi 5 or Proxmox LVM pools.
*   **Host Network Interfaces**
    *   `node_network_receive_errs_total`: Errors/dropped packets at the physical network interface card level (detects cable or switch faults).

### C. Application & Service Metrics
Deeper insights into the health of critical services running on the Homelab.

*   **Docker Containers (Pi 5 Host)**
    *   `container_cpu_usage_seconds_total` & `container_memory_usage_bytes`: Resource consumption per container (Caddy, Rathole, AdGuard Home, etc.) using `cAdvisor`.
*   **Database (Centralized PostgreSQL)**
    *   `pg_stat_activity_count`: Number of open DB connections (prevents resource starvation).
    *   `pg_database_size_bytes`: Storage footprint of PostgreSQL databases using `postgres_exporter`.
*   **SSL / TLS Certificates**
    *   `probe_ssl_earliest_cert_expiry`: Days remaining before Let's Encrypt certificates (managed by Caddy) expire, checked via `Blackbox Exporter`.
*   **S3 Storage (RustFS S3)**
    *   `s3_bucket_size_bytes`: Storage usage for private Docker registries or backups.
*   **Proxmox API**
    *   `pve_vm_status`: Active states of K8s VMs (Running/Stopped) using `proxmox_exporter`.

---

## 2. Solution Analysis & Architectural Decisions

The monitoring system is built on the following architectural design principles to adapt to resource constraints:

1.  **Resource Hard Limits at the Root:**
    Rather than merely alerting on resource saturation on the Raspberry Pi 5, we apply CPU and memory limits (`deploy.resources.limits`) directly in `docker-compose.yml` for heavier containers (`n8n`, `postgres`, `rustfs`). This ensures no single container can crash the gateway host.
2.  **No Intermediate Database for Normalization:**
    The system does **not** employ a secondary relational database (e.g., PostgreSQL or MongoDB) to aggregate and normalize metrics. Instead, **Prometheus acts as the dedicated Time-Series Database (TSDB)**. Exporters automatically expose data in the standard Prometheus Exposition Format, which Prometheus scrapes directly, saving processing overhead.

### Proposed Architecture: Kube-Prometheus-Stack + n8n ChatOps

Given the heterogeneous metrics (hardware router, hypervisor, K8s, Docker), we implement a **Pull-based Monitoring** topology.

```text
 [MikroTik Router] --(SNMP)--> [SNMP Exporter] --\
                                                  \
  [Pi 5 Gateway] -----> [Node Exporter] ----------> \
                                                     \    [K8s Cluster]
  [Proxmox Host] -----> [Node Exporter] ----------> [ Prometheus Server ] ---> [ Grafana ]
                                                     /         |
  [K8s Nodes/Pods] ---> [cAdvisor / Kube-State] ----/          | (Alert Webhook)
                                                               v
                                                      [ Alertmanager ]
                                                               | (Webhook JSON)
                                                               v
  [Telegram/Discord] <--(Chat & Alert Actions)--> [ n8n (Webhook & Bot Logic) ]
```


## 3. Implementation Roadmap

If you agree with this metric architecture design, we will proceed through 3 phases:

- **Phase 1: Collector Preparation**
  - Enable SNMP on the MikroTik router.
  - Install Node Exporter on the Pi 5 gateway and the Proxmox host using Ansible / Bash scripts.
- **Phase 2: Deploy Kube-Prometheus-Stack**
  - Package Prometheus, Alertmanager, and Grafana into Kubernetes via Helm/ArgoCD.
  - Add targets (Pi 5, Proxmox, MikroTik) to the Prometheus configuration file.
- **Phase 3: Configure n8n ChatOps Bot**
  - Set up n8n workflows to ingest HTTP webhooks from Alertmanager.
  - Establish a two-way interactive chatbot logic on n8n.