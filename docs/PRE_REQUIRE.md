---
type: Playbook
title: "Proxmox VE IaC Prerequisites"
description: "Guidelines on creating Proxmox VE API Tokens and SSH keys required for automated Terraform infrastructure provisioning"
timestamp: 2026-07-03T15:14:00Z
---

# Proxmox IaC Prerequisites & API Token Guide

This document details the preparatory steps (prerequisites) required to run Terraform and Ansible for the Kubernetes cluster on Proxmox.

---

## 1. Create Proxmox API Token (Crucial)

To allow Terraform to control Proxmox VE, you need an API Token. Avoid using the direct `root` password for API requests.

### Step 1: Create User and Role (Recommended)
While you can use the `root` user, it is highly recommended to create a dedicated user:
1. Go to Proxmox Web UI -> **Datacenter** -> **Permissions** -> **Users**.
2. Click **Add**:
   - User name: `terraform-user`
   - Realm: `pve` (Proxmox VE authentication server)
   - Password: Choose a secure password.
3. Add permissions: Click **Datacenter** -> **Permissions** -> **Add** -> **User Permission**:
   - Path: `/`
   - User: `terraform-user@pve`
   - Role: `Administrator` (or a custom role with restricted permissions for better security).

### Step 2: Create API Token
1. Go to **Datacenter** -> **Permissions** -> **API Tokens**.
2. Click **Add**:
   - User: Select `terraform-user@pve` (or `root@pam`).
   - Token ID: `homelab` (or any custom name).
   - **Uncheck** "Privilege Separation" for simplicity unless you need strict hierarchical permission management.
3. Click **Add**.
4. **SAVE IMMEDIATELY**: It will display the `Token ID` and `Secret`. You can only view this Secret **ONCE**.
   - Token ID format: `<PROXMOX_API_TOKEN_ID>`
   - Secret format: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`

---

## 2. Set Up SSH Keys

You need an SSH key pair for Terraform to inject into Cloud-Init, enabling passwordless login to the K8s VMs.

1. Check if you already have a key: `ls ~/.ssh/id_ed25519.pub` or `ls ~/.ssh/id_rsa.pub`.
2. If not, generate a new one:
   ```bash
   ssh-keygen -t ed25519 -C "your_email@example.com"
   ```
3. Copy the contents of the public key `.pub` file to paste into your `terraform.tfvars` file later.

---

## 3. Install Tools on Your Control Machine

Your local development machine (macOS/Linux/Windows WSL) must have the following tools installed:

- **Terraform (OpenTofu)**: [Download](https://developer.hashicorp.com/terraform/downloads) or run `brew install terraform`.
- **Ansible**: Run `brew install ansible` or `pip install ansible`.
- **sshpass** (Optional, to allow Ansible to automatically enter the SSH password on the first connection): Run `brew install esolitos/ipa/sshpass`.

---

## 4. Create VM Template on Proxmox

Terraform does not install the OS from scratch; it clones from a pre-configured template.

1. Copy the `create_template.sh` script to Proxmox:
   ```bash
   scp iac/create_template.sh root@<PROXMOX_IP>:/root/
   ```
2. SSH into Proxmox and run the script:
   ```bash
   ssh root@<PROXMOX_IP>
   bash /root/create_template.sh
   ```
   *This script downloads the Ubuntu Cloud-Init image and configures a VM Template with ID 9000.*

---

## 5. Configure Environment Variables for Terraform

Navigate to the `iac/terraform` directory and copy the template variable file:

```bash
cd iac/terraform
cp terraform.tfvars.example terraform.tfvars
```

Open `terraform.tfvars` and specify:
- `pm_api_url`: `https://<PROXMOX_IP>:8006/api2/json`
- `pm_api_token_id`: The Token ID obtained from Step 1.
- `pm_api_token_secret`: The Secret obtained from Step 1.
- `ssh_public_key`: The contents of the public key file from Step 2.

---

## Next Steps
Once the above steps are completed, you are ready to:
1. `terraform init`
2. `terraform apply`
(For more details, see `iac/README.md`)