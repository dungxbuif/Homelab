variable "proxmox_endpoint" {
  type        = string
  description = "TLS-certified node name. The controlled executor must map pve to 10.10.0.20."
  default     = "https://pve:8006/"
}

variable "proxmox_api_token" {
  type        = string
  description = "Proxmox API token supplied by Semaphore; never commit this value."
  sensitive   = true
}

variable "proxmox_tls_insecure" {
  type        = bool
  description = "Explicit bootstrap-only TLS bypass; production requires trusted TLS and the default false."
  default     = false
}

variable "proxmox_node" {
  type        = string
  description = "Existing Proxmox node hosting VM100."
  default     = "pve"
}

variable "vm_id" {
  type        = number
  description = "Existing production VM ID."
  default     = 100
}

variable "vm_name" {
  type        = string
  description = "Observed Proxmox VM name, supplied explicitly to prevent an import-time rename."
}

variable "cpu_cores" {
  type        = number
  description = "Imported VM100 vCPU count."
  default     = 6
}

variable "memory_mb" {
  type        = number
  description = "Imported VM100 memory in MiB."
  default     = 16384
}

variable "disk_datastore" {
  type        = string
  description = "Existing VM100 root disk datastore."
  default     = "local-lvm"
}

variable "disk_gib" {
  type        = number
  description = "Imported VM100 scsi0 size in GiB."
  default     = 200
}

variable "network_bridge" {
  type        = string
  description = "Existing VM100 LAN bridge."
  default     = "vmbr0"
}
