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
