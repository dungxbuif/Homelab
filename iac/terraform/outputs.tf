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
