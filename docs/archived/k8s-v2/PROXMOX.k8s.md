---
type: Playbook
title: "Proxmox HA Kubernetes Cluster Bootstrap Guide"
description: "Bootstrapping a high-availability control plane Kubernetes cluster on Proxmox VE nodes using Terraform and Ansible"
timestamp: 2026-07-03T15:14:00Z
---

# 🖥️ Proxmox & K8s Cluster Guide

This document details the management of Proxmox VE and the High-Availability (HA) Kubernetes cluster in the Homelab.

---

## 🏗️ Infrastructure Architecture

### 1. Proxmox Host Specifications
- **IP Address:** `<PROXMOX_IP>` (Web UI: `https://<PROXMOX_IP>:8006`)
- **Hardware:** 12 vCPUs, 32GB RAM.
- **Storage:** ~375GB LVM-Thin (`local-lvm`).

### 2. K8s Nodes List (VMs)
The Kubernetes cluster runs on 3 Ubuntu 22.04 LTS virtual machines:

| VM Name | VM ID | IP Address | Resources (vCPU/RAM/Disk) |
| :--- | :--- | :--- | :--- |
| **k8s-cp-1** | 100 | `<K8S_CP1_IP>` | 4 Cores / 10GB RAM / 80GB SSD |
| **k8s-cp-2** | 101 | `<K8S_CP2_IP>` | 4 Cores / 10GB RAM / 80GB SSD |
| **k8s-cp-3** | 102 | `<K8S_CP3_IP>` | 4 Cores / 10GB RAM / 80GB SSD |

*Note: The default Ubuntu template uses VM ID 9000.*

---

## ☸️ Kubernetes HA Cluster Configuration

### 1. Core Parameters
- **Kubernetes Version:** `1.30.14`
- **Control Plane Endpoint (VIP):** `<K8S_VIP>:6443` (Managed by `kube-vip`)
- **CNI:** Cilium (eBPF Mode)
- **Container Runtime:** `containerd://2.2.1`

### 2. High Availability (HA) Mechanism
The cluster utilizes a **Stacked etcd topology**. `kube-vip` assigns the Virtual IP (VIP) `<K8S_VIP>` to the `eth0` interface of the current Leader node. If the Leader node fails, the VIP automatically transitions to one of the remaining control plane nodes.

### 3. Provisioning Workflow (IaC)
The entire VM provisioning and K8s installation process is automated using:
- **Terraform:** VM provisioning on Proxmox (`iac/terraform/`).
- **Ansible:** Operating system configuration and K8s bootstrapping (`iac/ansible/`).
- **Master Script:** `bash iac/deploy.sh` (Orchestrates the end-to-end flow).

---

## 💾 Storage (Longhorn)

### 1. Strategic Decisions (2026-06-03)
- **Version:** Longhorn v1.7.x (Engine V1).
    - *Rationale:* Highly stable and consumes fewer CPU/RAM resources than Engine V2 under VirtIO virtualization environments.
- **Deployment Method:** Manual installation (Helm/YAML) via Ansible.
- **Disk Configuration:** Uses `/var/lib/longhorn` directly on the existing 80GB OS disk.
- **HA Replication Configuration:**
    - **Strategy:** 2 Replicas across 3 Nodes.
    - **Rationale:** Ensures no data loss if a single node fails, while saving 33% disk space compared to the default 3 replicas. The third node acts as a "spare" to automatically rebuild degraded volumes.
- **Protection Mechanisms:**
    - **Storage Minimal Available:** 15% (~12GB). Longhorn automatically blocks writes if the OS disk space drops below 15% to prevent the VM from hanging.
    - **Resource Reservation:** Reserves 10% CPU for Engine and Replica managers to ensure stable I/O latency.

### 2. Prerequisites
All nodes must have the following services installed and enabled:
- `open-iscsi` (Service status must be `running`).
- `nfs-common`.

---

## 🪵 Key Troubleshooting Registry (Bootstrap Fixes)

During the initial deployment (2026-06-03), we identified and resolved the following issues:

1.  **VIP Loop Error (Kube-vip loop):** `kube-vip` could not bind the VIP because it couldn't connect to the API Server, but the API Server needed the VIP to start.
    *   **Fix:** Added `127.0.0.1 kubernetes` to `/etc/hosts` to allow `kube-vip` to connect to the local API Server immediately during bootstrap.
2.  **Proxmox Provider Issue:** Required explicit configuration of `slot = "scsi0"` and `type = "disk"` in Terraform to ensure compatibility with modern Proxmox API versions.
3.  **Cloud-Init Drive Missing:** Had to explicitly define the `cloudinit` drive at `ide2` for Proxmox to configure networks and apply SSH keys correctly.
4.  **K8s DNS Search Path Loop (2026-06-23):** Resolved high-volume query loops for deprecated `kubernetes.nccsoft.office` domain caused by Cloud-Init search domain inheritance. Fixed by replacing `nccsoft.office` with `lan` in VM Netplan configs (`netplan apply`) and updating Terraform config (`searchdomain = "lan"`) to prevent future regressions.


---

## 🛠️ Operations Guide

### 1. Access the Cluster from macOS
Use the automatically downloaded kubeconfig file:
```bash
export KUBECONFIG=~/.kube/config-homelab
kubectl get nodes
```

### 2. Check Kube-vip Logs
If the VIP `<K8S_VIP>` is unreachable:
```bash
ssh -i <K8S_SSH_PRIVATE_KEY_PATH> ubuntu@<K8S_CP1_IP> "sudo crictl logs \$(sudo crictl ps -a | grep kube-vip | awk '{print \$1}')"
```

### 3. Enable Hubble UI (Network Observability)
```bash
cilium hubble enable --ui
cilium hubble ui
```