terraform {
  encryption {
    key_provider "pbkdf2" "db_ops" {
      passphrase = var.state_encryption_passphrase
      iterations = 600000
    }
    method "aes_gcm" "db_ops" { keys = key_provider.pbkdf2.db_ops }
    state {
      method   = method.aes_gcm.db_ops
      enforced = true
    }
    plan {
      method   = method.aes_gcm.db_ops
      enforced = true
    }
  }
}
