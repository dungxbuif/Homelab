---
type: Concept
title: "Proxmox VM & K8s IaC Design Specification"
description: "Architectural design for VM provisioning and HA Kubernetes bootstrapping on Proxmox hypervisor nodes via Terraform/Ansible"
timestamp: 2026-07-03T15:14:00Z
---

# Design Spec: K8s HA Cluster on Proxmox (IaC)

**Date:** 2026-05-29
**Status:** Draft
**Topic:** Setup and deploy a 3-node HA Kubernetes cluster on Proxmox using Terraform and Ansible.

## 1. Overview
This system aims to automate the deployment of a High Availability (HA) Kubernetes cluster on Proxmox VE. It uses Infrastructure as Code (IaC) to ensure reproducibility and easy management.

## 2. Technical Stack
- **Infrastructure Provider:** Proxmox VE (3 Nodes physical setup).
- **IaC Tools:** 
    - **Terraform (OpenTofu):** Manages VM creation and configuration (CPU, RAM, Disk, Network) on Proxmox.
    - **Ansible:** Manages OS configuration, runtime installation (containerd), and K8s cluster bootstrapping.
- **Kubernetes Distribution:** Vanilla Kubernetes (Kubeadm).
- **HA Strategy:** 3 Control Plane nodes (Stacked etcd).
- **Load Balancing (Control Plane):** Kube-vip (Virtual IP for API Server).
- **Container Runtime:** Containerd.
- **Networking (CNI):** Calico or Flannel (to be decided based on available resources).

## 3. Architecture & Components
### 3.1. Infrastructure Layer (Terraform)
- **VMs:** 3 VMs on Proxmox.
- **Resources:** Flexible (to be traced from Proxmox credentials).
- **Template:** Cloud-Init (Ubuntu 22.04 or 24.04 LTS).

### 3.2. Configuration Layer (Ansible)
- **Roles:**
    - `common`: Install basic packages, disable swap, configure sysctl parameters.
    - `runtime`: Install containerd runtime.
    - `kubeadm`: Install kubelet, kubeadm, and kubectl.
    - `master`: Initialize the first master node with Kube-vip, join subsequent master nodes.
    - `networking`: Deploy CNI.

### 3.3. Proxmox Integration
- Uses API Tokens / User Credentials for Terraform and Ansible to interact with Proxmox.
- Autodetect available Storage and Network Bridges.

## 4. Security & Compliance
- **Credential Protection:** Proxmox authentication details will be stored in a `.env` or `vars_file` (which are gitignored).
- **Portless Principle:** Follows the existing Homelab architecture (accessible via administrative VPN overlay).

## 5. Next Steps
1. User confirmation of the design spec.
2. Set up Terraform environment (Proxmox Provider).
3. Write Ansible Playbooks.
4. Test deployment on 1 node, then scale up to a 3-node HA configuration.