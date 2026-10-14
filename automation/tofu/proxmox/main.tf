resource "proxmox_virtual_environment_vm" "vm100" {
  node_name   = var.proxmox_node
  vm_id       = var.vm_id
  name        = var.vm_name
  description = "Managed import-only baseline for production VM100"
  started     = true
  on_boot     = true
  protection  = true

  cpu {
    cores = var.cpu_cores
    type  = "host"
  }

  memory {
    dedicated = var.memory_mb
  }

  agent {
    enabled = true
  }

  operating_system {
    type = "l26"
  }

  disk {
    datastore_id = var.disk_datastore
    interface    = "scsi0"
    size         = var.disk_gib
    discard      = "on"
    iothread     = true
  }

  network_device {
    bridge = var.network_bridge
    model  = "virtio"
  }

  lifecycle {
    prevent_destroy = true
  }
}
