resource "proxmox_virtual_environment_vm" "vm100" {
  node_name     = var.proxmox_node
  vm_id         = var.vm_id
  name          = var.vm_name
  started       = true
  on_boot       = true
  protection    = false
  scsi_hardware = "virtio-scsi-pci"

  cpu {
    cores = var.cpu_cores
    type  = "host"
  }

  memory {
    dedicated = var.memory_mb
    floating  = 0
  }

  agent {
    enabled = true
  }

  disk {
    datastore_id = var.disk_datastore
    interface    = "scsi0"
    size         = var.disk_gib
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
        address = "10.10.0.31/24"
        gateway = "10.10.0.1"
      }
    }

    user_account {
      username = "ubuntu"
      keys = [
        "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIJrm7NEwiBT2A6gSbt+hiUBq4gRHWE94dxsAwFiz5eIp homelab-vm100-iac",
      ]
    }
  }

  network_device {
    bridge      = var.network_bridge
    model       = "virtio"
    mac_address = "8E:8D:DC:BD:7F:72"
  }

  lifecycle {
    prevent_destroy = true
    # Proxmox masks the existing cloud-init password; never rotate it during import.
    ignore_changes = [initialization[0].user_account[0].password]
  }
}
