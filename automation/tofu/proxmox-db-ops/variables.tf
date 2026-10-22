variable "proxmox_endpoint" {
  type    = string
  default = "https://pve:8006/"
}
variable "proxmox_api_token" {
  type      = string
  sensitive = true
}
variable "proxmox_tls_insecure" {
  type    = bool
  default = false
}
variable "proxmox_node" {
  type    = string
  default = "pve"
}
variable "vm_id" {
  type    = number
  default = 110
}
variable "template_vm_id" {
  type    = number
  default = 9000
}
variable "vm_name" {
  type    = string
  default = "db-ops"
}
variable "ssh_public_key" {
  type      = string
  sensitive = true
}
variable "state_encryption_passphrase" {
  type      = string
  sensitive = true
  validation {
    condition     = length(var.state_encryption_passphrase) >= 32
    error_message = "The state encryption passphrase must contain at least 32 characters."
  }
}
