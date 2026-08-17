---
type: Reference
title: "Proxmox Hypervisor Guide (AWS Lab Repurpose)"
description: "Proxmox VE hypervisor role after the K8s cluster retirement — repurposed as a self-hosted AWS practice lab"
timestamp: 2026-08-17T00:00:00Z
---

# 🖥️ Proxmox VE Guide (AWS Lab Repurpose)

> **Host:** Proxmox VE — LAN IP `10.10.0.20` / Tailnet `100.64.0.3` — 12 vCPUs / 32 GB RAM / ~375 GB LVM-Thin.
> **Current role:** Self-hosted **AWS practice lab** (LocalStack / EKS-like clusters / eksctl / SAA study).
> **Previous role (retired 2026-08):** 3-node HA Kubernetes cluster host. Those docs are archived in [`archived/k8s-v2/`](./archived/).

---

## 🔄 Role Change (2026-08)

The Proxmox host used to run three Ubuntu VMs (`k8s-cp-1/2/3`, VM IDs 100–102)
forming a stacked-etcd HA Kubernetes cluster (VIP `10.10.0.30` via kube-vip,
Traefik ingress, Longhorn storage, ArgoCD GitOps). All user-facing workloads from
that cluster were **migrated to the Mac mini** (`10.10.0.10`) — see
[MAC.md](./MAC.md) and the archived migration record
[`archived/k8s-v2/k8s/migration_k8s_to_mac.md`](./archived/k8s-v2/k8s/migration_k8s_to_mac.md).

After the migration the K8s app namespaces were deleted and the cluster is
being **torn down**. The Proxmox host is now repurposed as a self-hosted AWS lab:
- **Goal:** hands-on practice for AWS SAA certification and EKS / managed-service
  workflows that map cleanly to AWS.
- **Tooling:** LocalStack (AWS emulator), k3s/eksctl-style clusters, Terraform
  against the Proxmox API for ephemeral VMs, Ansible for OS config.
- **Lifecycle:** lab VMs are **ephemeral** — spin up, practice, tear down. No
  persistent production state lives on Proxmox anymore.

The full K8s-era operational history (cluster bootstrap, Longhorn config review,
recovery guide, DB inventory, CICD) is preserved in
[`archived/k8s-v2/`](./archived/k8s-v2/) for reference.

---

## 🔧 IaC Prerequisites (still applicable)

Provisioning lab VMs on Proxmox still uses Terraform + Ansible against the
Proxmox API. The prerequisite setup (API tokens, SSH keys) is unchanged:

📖 [PRE_REQUIRE.md](./PRE_REQUIRE.md) — Proxmox VE API token & SSH key setup for
Terraform/Ansible automation. (The procedure is generic; only the *purpose*
shifted from K8s to AWS-lab VMs.)

---

## 🗂️ Existing IaC Layout

```
iac/
├── terraform/        # Proxmox VM provisioning (Terraform/OpenTofu)
└── ansible/          # OS config + runtime install (group_vars, roles)
```

> [!NOTE]
> `iac/terraform/` still holds the **K8s cluster** state (`terraform.tfstate` for
> `k8s-cp-1/2/3`). Before reusing it for the AWS lab, back up that state and
> branch a new working directory (e.g. `iac/terraform/aws-lab/`) so a stray
> `terraform destroy` does not touch any still-running K8s nodes until the
> cluster teardown is confirmed.

---

## ✅ Recommended Next Steps for the AWS Lab

1. **Confirm K8s cluster teardown** (the 3 Proxmox VMs can be destroyed via
   `terraform destroy` in `iac/terraform/` — this is a separate, destructive
   infra action; do not run it unattended).
2. **Branch the IaC** into `iac/terraform/aws-lab/` with its own state, keyed by
   lab name (e.g. `eks-practice`, `localstack`). Lab VMs should be tagged so they
   are easy to filter and destroy.
3. **LocalStack** — run the AWS emulator (S3, SQS, Lambda, etc.) either as a
   Proxmox VM container or docker-compose on a lab VM. The previous K8s
   LocalStack deployment (namespace `localstack`, retired) is archived at
   [`iac/k8s/localstack/`](../iac/k8s/localstack/) for reference config.
4. **eksctl / k3s** — practice EKS-style managed clusters using k3s on Proxmox
   VMs to approximate AWS managed Kubernetes without the cloud bill.
5. **Teardown discipline** — lab VMs are disposable. Document a one-command
   `terraform destroy -var lab=<name>` workflow so nothing lingers.
