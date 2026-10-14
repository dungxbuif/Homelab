output "vm100_id" {
  value = proxmox_virtual_environment_vm.vm100.vm_id
}

output "vm100_node" {
  value = proxmox_virtual_environment_vm.vm100.node_name
}

output "vm100_name" {
  value = proxmox_virtual_environment_vm.vm100.name
}

output "vm100_lan_ip" {
  value = "10.10.0.31"
}
