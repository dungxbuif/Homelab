---
type: Reference
title: "Longhorn Persistent Storage Review"
description: "Performance review, configuration tuning, and replica scheduling recommendations for Longhorn storage on K8s"
timestamp: 2026-07-03T15:14:00Z
---

# 📋 Longhorn v1.7.x Configuration - Review

Below are the key configuration parameters prepared for the Longhorn deployment. These values are optimized for a 3-node HA server configuration with limited disk capacity.

## 1. Storage Settings

| Parameter | Value | Detailed Description |
| :--- | :--- | :--- |
| **`defaultDataPath`** | `/var/lib/longhorn` | Directory on the VMs' 80GB OS disks where the actual volume block data is stored. |
| **`defaultNumberOfReplicas`** | `2` | Each volume is replicated across 2 separate nodes. Ensures data remains safe if 1 node fails, while saving 33% storage capacity compared to the default 3 replicas. |
| **`storageOverProvisioningPercentage`** | `150` | Allows over-provisioning of storage capacity. For example, if you have 100GB of physical space, you can allocate up to 150GB of virtual volumes. Requires monitoring to avoid physical disk exhaustion. |
| **`storageMinimalAvailablePercentage`** | `15` | Longhorn stops writes to disk if free OS disk space drops below 15% (protects the host OS from locking up due to disk exhaustion). |

## 2. Resource & Performance Settings

| Parameter | Value | Detailed Description |
| :--- | :--- | :--- |
| **`guaranteedEngineManagerCPU`** | `10%` | CPU limit dedicated to Engine management. For hosts with 2-4 cores, 10% is sufficient to ensure stable execution without bottlenecking application workloads. |
| **`guaranteedReplicaManagerCPU`** | `10%` | CPU limit dedicated to Replica management. |
| **`priorityClass`** | `system-cluster-critical` | Sets the highest execution priority. If the cluster runs low on memory, Kubernetes evicts other applications first to protect Longhorn processes from corruption. |

## 3. High Availability Settings

| Parameter | Value | Detailed Description |
| :--- | :--- | :--- |
| **`allowNodeFailureWithLastReplica`** | `true` | Allows volumes to remain online even if only 1 replica remains available (useful during rolling maintenance or node outages). |
| **`replicaSoftAntiAffinity`** | `true` | Allows placing two replicas on the same node if no other healthy node is available in the cluster (set to `true` for flexibility, though distinct host scheduling is preferred). |
| **`upgradeChecker`** | `false` | Disables automated checks for new releases to limit outbound public traffic and maintain system stability. |

---

## 🛠️ Proposed Installation Commands

We will install Longhorn manually using Helm:

```bash
helm repo add longhorn https://charts.longhorn.io
helm repo update
helm install longhorn longhorn/longhorn \
  --namespace longhorn-system \
  --create-namespace \
  --values values.yaml
```

**Do you agree with the configuration parameters outlined above? Especially sharing the primary OS disk volume and utilizing a default replica count of 2?**