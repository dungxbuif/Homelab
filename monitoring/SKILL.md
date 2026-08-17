---
name: homelab-monitor
slug: homelab-monitor
description: Tự động kiểm tra và báo cáo trạng thái sức khỏe hệ thống Homelab, Kubernetes Cluster, Proxmox VE, Cloud VPS, Docker containers, CPU/RAM/Disk, và băng thông MikroTik Router CHỈ THÔNG QUA DOMAIN GRAFANA (https://grafana.dungxbuif.com). BẮT BUỘC sử dụng skill này khi người dùng hỏi về tình trạng hệ thống, metrics, Grafana, VictoriaMetrics, CPU/RAM/Disk, nhiệt độ chip, hoặc danh sách containers/Pods.
tags: [monitoring, homelab, grafana, promql, k8s]
timestamp: 2026-08-11T22:00:00+07:00
---

# 📊 Homelab Monitoring Skill

Skill hướng dẫn AI Agent **truy vấn PromQL, kiểm tra sức khỏe hệ thống Homelab** duy nhất thông qua domain **`https://grafana.dungxbuif.com`**.

---

## 🔒 1. Security Policy & Connection Rules

* **Domain duy nhất:** `https://grafana.dungxbuif.com` — SSL Let's Encrypt `*.dungxbuif.com` hợp lệ 100%, KHÔNG cần `-k`.
* **Auth:** `admin` / `D8tkeMG3k4A8Nq2` (Basic Auth header: `Authorization: Basic YWRtaW46RDh0a2VNRzNrNEE4TnEy`)
* **Datasource Proxy Base URL:**
  ```
  https://grafana.dungxbuif.com/api/datasources/proxy/uid/P4169E866C3094E38/api/v1/query
  ```
* **Tool nên dùng trong sandbox:** `exec` với lệnh `curl` (đã cài sẵn). KHÔNG dùng `web_fetch` vì không truyền được Basic Auth header đúng cách.

---

## 🔄 2. Workflow

1. **Bước 1 — Check Target Health:** Query `up` — xác nhận 9/9+ scrape targets ONLINE.
2. **Bước 2 — Query Resource Metrics:** Dùng các lệnh cURL chuẩn theo category bên dưới.
3. **Bước 3 — Synthesize & Report:** Báo cáo tổng hợp với Dashboard Links.

---

## 💻 3. PromQL cURL Query Library (17 Queries Đầy Đủ)

> **Template chung:** Thay `QUERY` bằng PromQL query cần chạy:
> ```bash
> curl -s -u admin:D8tkeMG3k4A8Nq2 "https://grafana.dungxbuif.com/api/datasources/proxy/uid/P4169E866C3094E38/api/v1/query?query=QUERY"
> ```

---

### 🟢 A. Target Health

#### 1. Scrape Targets Online/Offline:
```bash
curl -s -u admin:D8tkeMG3k4A8Nq2 "https://grafana.dungxbuif.com/api/datasources/proxy/uid/P4169E866C3094E38/api/v1/query?query=up" | jq '.data.result[] | {job: .metric.job, instance: .metric.instance, status: .value[1]}'
```

---

### 🔴 B. CPU Usage % Real-time

#### 2. CPU Usage % per Host (irate 5m):
```bash
curl -s -u admin:D8tkeMG3k4A8Nq2 "https://grafana.dungxbuif.com/api/datasources/proxy/uid/P4169E866C3094E38/api/v1/query?query=100-(avg+by(job)(irate(node_cpu_seconds_total%7Bmode%3D%22idle%22%7D%5B5m%5D))*100)" | jq '.data.result[] | {job: .metric.job, cpu_used_percent: (.value[1] | tonumber | round)}'
```

#### 3. Docker CPU % per Container (rate 5m):
```bash
curl -s -u admin:D8tkeMG3k4A8Nq2 "https://grafana.dungxbuif.com/api/datasources/proxy/uid/P4169E866C3094E38/api/v1/query?query=sum+by(name)(rate(container_cpu_usage_seconds_total%7Bname!%3D%22%22%7D%5B5m%5D))*100" | jq '.data.result[] | select(.metric.name != null) | {container: .metric.name, cpu_percent: (.value[1] | tonumber * 100 | round / 100)}'
```

---

### 💾 C. Memory & Swap

#### 4. RAM Usage % per Host:
```bash
curl -s -u admin:D8tkeMG3k4A8Nq2 "https://grafana.dungxbuif.com/api/datasources/proxy/uid/P4169E866C3094E38/api/v1/query?query=100*(1-(node_memory_MemAvailable_bytes/node_memory_MemTotal_bytes))" | jq '.data.result[] | {job: .metric.job, ram_used_percent: (.value[1] | tonumber | round)}'
```

#### 5. Swap Usage % per Host:
```bash
curl -s -u admin:D8tkeMG3k4A8Nq2 "https://grafana.dungxbuif.com/api/datasources/proxy/uid/P4169E866C3094E38/api/v1/query?query=100*(1-(node_memory_SwapFree_bytes/node_memory_SwapTotal_bytes))" | jq '.data.result[] | select((.value[1] | tonumber) > 0) | {job: .metric.job, swap_used_percent: (.value[1] | tonumber | round)}'
```

---

### 🔴 D. Disk

#### 6. Disk I/O Read Speed MB/s (rate 5m):
```bash
curl -s -u admin:D8tkeMG3k4A8Nq2 "https://grafana.dungxbuif.com/api/datasources/proxy/uid/P4169E866C3094E38/api/v1/query?query=rate(node_disk_read_bytes_total%5B5m%5D)/1048576" | jq '.data.result[] | {job: .metric.job, device: .metric.device, read_mbs: (.value[1] | tonumber * 100 | round / 100)}'
```

#### 7. Disk I/O Write Speed MB/s (rate 5m):
```bash
curl -s -u admin:D8tkeMG3k4A8Nq2 "https://grafana.dungxbuif.com/api/datasources/proxy/uid/P4169E866C3094E38/api/v1/query?query=rate(node_disk_written_bytes_total%5B5m%5D)/1048576" | jq '.data.result[] | {job: .metric.job, device: .metric.device, write_mbs: (.value[1] | tonumber * 100 | round / 100)}'
```

#### 8. Disk Free Space GB:
```bash
curl -s -u admin:D8tkeMG3k4A8Nq2 "https://grafana.dungxbuif.com/api/datasources/proxy/uid/P4169E866C3094E38/api/v1/query?query=node_filesystem_avail_bytes%7Bfstype!%3D%22tmpfs%22%7D" | jq '.data.result[] | {instance: .metric.instance, mountpoint: .metric.mountpoint, avail_gb: (.value[1] | tonumber / 1073741824 | round)}'
```

---

### 📡 E. Network Bandwidth Real-time

#### 9. Network RX Mbps per Host (rate 5m):
```bash
curl -s -u admin:D8tkeMG3k4A8Nq2 "https://grafana.dungxbuif.com/api/datasources/proxy/uid/P4169E866C3094E38/api/v1/query?query=rate(node_network_receive_bytes_total%7Bdevice!%3D%22lo%22%7D%5B5m%5D)*8/1048576" | jq '.data.result[] | {job: .metric.job, device: .metric.device, rx_mbps: (.value[1] | tonumber * 100 | round / 100)}'
```

#### 10. Network TX Mbps per Host (rate 5m):
```bash
curl -s -u admin:D8tkeMG3k4A8Nq2 "https://grafana.dungxbuif.com/api/datasources/proxy/uid/P4169E866C3094E38/api/v1/query?query=rate(node_network_transmit_bytes_total%7Bdevice!%3D%22lo%22%7D%5B5m%5D)*8/1048576" | jq '.data.result[] | {job: .metric.job, device: .metric.device, tx_mbps: (.value[1] | tonumber * 100 | round / 100)}'
```

---

### 🖥️ F. Proxmox VE — Per VM

#### 11. Proxmox VM CPU % per VM:
```bash
curl -s -u admin:D8tkeMG3k4A8Nq2 "https://grafana.dungxbuif.com/api/datasources/proxy/uid/P4169E866C3094E38/api/v1/query?query=pve_cpu_usage_ratio*100" | jq '.data.result[] | {vm: .metric.id, cpu_percent: (.value[1] | tonumber * 100 | round / 100)}'
```

#### 12. Proxmox VM Memory Usage MB per VM:
```bash
curl -s -u admin:D8tkeMG3k4A8Nq2 "https://grafana.dungxbuif.com/api/datasources/proxy/uid/P4169E866C3094E38/api/v1/query?query=pve_memory_usage_bytes/1048576" | jq '.data.result[] | {vm: .metric.id, mem_used_mb: (.value[1] | tonumber | round)}'
```

---

### 🔌 G. Service Health Check (Blackbox Exporter)

#### 13. HTTP/TCP Service Health (probe_success = 1 = OK):
```bash
curl -s -u admin:D8tkeMG3k4A8Nq2 "https://grafana.dungxbuif.com/api/datasources/proxy/uid/P4169E866C3094E38/api/v1/query?query=probe_success" | jq '.data.result[] | {service: .metric.instance, healthy: (if .value[1] == "1" then "UP" else "DOWN" end)}'
```

#### 14. HTTP Response Time ms per Service:
```bash
curl -s -u admin:D8tkeMG3k4A8Nq2 "https://grafana.dungxbuif.com/api/datasources/proxy/uid/P4169E866C3094E38/api/v1/query?query=probe_duration_seconds*1000" | jq '.data.result[] | {service: .metric.instance, response_ms: (.value[1] | tonumber | round)}'
```

---

### ☸️ H. Kubernetes

#### 15. K8s Pod Status (Running/Pending/Failed):
```bash
curl -s -u admin:D8tkeMG3k4A8Nq2 "https://grafana.dungxbuif.com/api/datasources/proxy/uid/P4169E866C3094E38/api/v1/query?query=sum(kube_pod_status_phase)by(phase)" | jq '.data.result[] | {phase: .metric.phase, count: .value[1]}'
```

#### 16. K8s Nodes Ready:
```bash
curl -s -u admin:D8tkeMG3k4A8Nq2 "https://grafana.dungxbuif.com/api/datasources/proxy/uid/P4169E866C3094E38/api/v1/query?query=kube_node_status_condition%7Bcondition%3D%27Ready%27%2Cstatus%3D%27true%27%7D" | jq '.data.result[] | {node: .metric.node, ready: .value[1]}'
```

#### 17. CPU Temp per Host (°C):
```bash
curl -s -u admin:D8tkeMG3k4A8Nq2 "https://grafana.dungxbuif.com/api/datasources/proxy/uid/P4169E866C3094E38/api/v1/query?query=node_hwmon_temp_celsius" | jq '.data.result[] | {job: .metric.job, chip: .metric.chip, temp_celsius: .value[1]}'
```

---

## 🔗 4. Grafana Dashboard URLs

* **Login:** `https://grafana.dungxbuif.com` → `admin` / `D8tkeMG3k4A8Nq2`

| Thành Phần | Dashboard Link |
| :--- | :--- |
| **Kubernetes Cluster & Pods** | [k8s-views-pods](https://grafana.dungxbuif.com/d/k8s_views_pods/kubernetes-views-pods) |
| **Node Exporter Full (Hosts)** | [node-exporter-full](https://grafana.dungxbuif.com/d/rYdddlPWk/node-exporter-full) |
| **cAdvisor Docker Containers** | [cadvisor-exporter](https://grafana.dungxbuif.com/d/pMEd7m0Mz/cadvisor-exporter) |
| **Proxmox VE & VMs** | [proxmox-via-prometheus](https://grafana.dungxbuif.com/d/Dp7Cd57Zza/proxmox-via-prometheus) |
| **PostgreSQL Database** | [postgresql-database](https://grafana.dungxbuif.com/d/000000039/postgresql-database) |
| **MikroTik Router** | [mikrotik-monitoring](https://grafana.dungxbuif.com/d/nR3NRDGaz/mikrotik-monitoring) |
