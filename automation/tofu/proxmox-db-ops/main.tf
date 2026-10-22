resource "proxmox_virtual_environment_vm" "db_ops" {
  node_name     = var.proxmox_node
  vm_id         = var.vm_id
  name          = var.vm_name
  started       = true
  on_boot       = true
  protection    = true
  scsi_hardware = "virtio-scsi-pci"

  clone {
    vm_id = var.template_vm_id
    full  = true
  }
  cpu {
    cores = 4
    type  = "host"
  }
  memory {
    dedicated = 8192
    floating  = 0
  }
  agent {
    enabled = true
  }

  disk {
    datastore_id = "local-lvm"
    interface    = "scsi0"
    size         = 80
    discard      = "on"
    iothread     = false
    replicate    = false
  }

  initialization {
    datastore_id = "local-lvm"
    interface    = "ide2"
    upgrade      = false
    dns {
      servers = ["10.10.0.5", "1.1.1.1"]
    }
    ip_config {
      ipv4 {
        address = "10.10.0.32/24"
        gateway = "10.10.0.1"
      }
    }
    user_account {
      username = "ubuntu"
      keys     = [var.ssh_public_key]
    }
  }

  network_device {
    bridge      = "vmbr0"
    model       = "virtio"
    mac_address = "BC:24:11:34:34:5F"
  }

  lifecycle {
    prevent_destroy = true
    ignore_changes  = [initialization[0].user_account[0].password]
  }
}
