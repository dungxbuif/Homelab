---
type: Reference
title: "Code Index: terraform"
description: "Aggregated code index for terraform folder"
timestamp: 2026-07-03T15:11:00Z
---

# Code Index: terraform

> This index aggregates code files in the [[terraform/]] directory.
> Edit the source files directly; this index is auto-generated for Obsidian reading.

---

## [main.tf](./main.tf)

```terraform
terraform {
  required_providers {
    proxmox = {
      source  = "telmate/proxmox"
      version = "3.0.1-rc4"
    }
    local = {
      source  = "hashicorp/local"
      version = "2.5.2"
    }
  }
}

provider "proxmox" {
  pm_api_url          = var.pm_api_url
  pm_api_token_id     = var.pm_api_token_id
  pm_api_token_secret = var.pm_api_token_secret
  pm_tls_insecure     = true
}

resource "proxmox_vm_qemu" "k8s_nodes" {
  for_each    = var.k8s_nodes
  name        = each.key
  vmid        = each.value.vmid
  target_node = var.proxmox_host
  clone       = var.template_name
  full_clone  = true

  os_type  = "cloud-init"
  cores    = each.value.cores
  sockets  = 1
  cpu      = "host"
  memory   = each.value.memory
  scsihw   = "virtio-scsi-pci"
  bootdisk = "scsi0"
  agent    = 1
  onboot   = true

  disk {
    slot    = "scsi0"
    size    = each.value.disk
    type    = "disk"
    storage = var.storage
  }

  disk {
    slot    = "ide2"
    type    = "cloudinit"
    storage = var.storage
  }

  network {
    model  = "virtio"
    bridge = var.nic_name
  }

  ciuser       = var.ci_user
  nameserver   = join(" ", var.dns_servers)
  searchdomain = "lan"
  ipconfig0    = "ip=${each.value.ip}/${var.network_prefix},gw=${var.gw_ip}"
  sshkeys      = var.ssh_public_key
}

resource "local_file" "ansible_inventory" {
  filename = "${path.module}/../ansible/inventory.ini"
  content = templatefile("${path.module}/inventory.ini.tftpl", {
    ci_user  = var.ci_user
    vip      = var.kube_vip
    nodes    = var.k8s_nodes
    endpoint = "${var.kube_vip}:6443"
  })
}

```

---

## [outputs.tf](./outputs.tf)

```terraform
output "kube_vip" {
  value = var.kube_vip
}

output "kube_api_endpoint" {
  value = "${var.kube_vip}:6443"
}

output "k8s_nodes" {
  value = {
    for name, node in var.k8s_nodes : name => {
      vmid = node.vmid
      ip   = node.ip
    }
  }
}

output "ansible_inventory" {
  value = local_file.ansible_inventory.filename
}

```

---

## [variables.tf](./variables.tf)

```terraform
variable "pm_api_url" {
  type = string
}

variable "pm_api_token_id" {
  type = string
}

variable "pm_api_token_secret" {
  type      = string
  sensitive = true
}

variable "proxmox_host" { default = "pve" }
variable "template_name" { default = "ubuntu-22.04-template" }
variable "nic_name" { default = "vmbr0" }
variable "storage" { default = "local-lvm" }
variable "gw_ip" { default = "<MIKROTIK_IP>" }
variable "network_prefix" { default = 24 }
variable "kube_vip" { default = "<K8S_VIP>" }
variable "ci_user" { default = "ubuntu" }
variable "dns_servers" {
  type    = list(string)
  default = ["<PI_IP>", "1.1.1.1"]
}

variable "ssh_public_key" {
  type = string
}

variable "k8s_nodes" {
  type = map(object({
    vmid   = number
    ip     = string
    cores  = number
    memory = number
    disk   = string
  }))

  default = {
    k8s-cp-1 = {
      vmid   = 9101
      ip     = "<K8S_CP1_IP>"
      cores  = 2
      memory = 4096
      disk   = "30G"
    }
    k8s-cp-2 = {
      vmid   = 9102
      ip     = "<K8S_CP2_IP>"
      cores  = 2
      memory = 4096
      disk   = "30G"
    }
    k8s-cp-3 = {
      vmid   = 9103
      ip     = "<K8S_CP3_IP>"
      cores  = 2
      memory = 4096
      disk   = "30G"
    }
  }
}

```

---
