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

  operating_system {
    type = "other"
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
  }

  network_device {
    bridge      = var.network_bridge
    model       = "virtio"
    mac_address = "8E:8D:DC:BD:7F:72"
  }

  lifecycle {
    prevent_destroy = true
  }
}
