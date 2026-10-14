variable "state_encryption_passphrase" {
  type        = string
  sensitive   = true
  description = "Recoverable state key injected by the executor secret store; never store in tfvars."

  validation {
    condition     = length(var.state_encryption_passphrase) >= 32
    error_message = "The state encryption passphrase must contain at least 32 characters."
  }
}

terraform {
  encryption {
    key_provider "pbkdf2" "vm100" {
      passphrase = var.state_encryption_passphrase
      iterations = 600000
    }

    method "aes_gcm" "vm100" {
      keys = key_provider.pbkdf2.vm100
    }

    state {
      method   = method.aes_gcm.vm100
      enforced = true
    }

    plan {
      method   = method.aes_gcm.vm100
      enforced = true
    }
  }
}
