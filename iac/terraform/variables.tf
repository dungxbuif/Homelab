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
