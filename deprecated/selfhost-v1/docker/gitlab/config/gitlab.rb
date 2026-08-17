external_url 'https://gitlab.dungxbuif.com'
registry_external_url 'https://registry-gitlab.dungxbuif.com'

nginx['listen_port'] = 80
nginx['listen_https'] = false
letsencrypt['enable'] = false

# Disable SSL for registry since Cloudflare handles HTTPS
registry_nginx['listen_https'] = false

# Configure SSH access
gitlab_rails['gitlab_shell_ssh_port'] = 22

# Registry configuration
gitlab_rails['registry_enabled'] = true
registry_nginx['enable'] = true
registry_nginx['listen_port'] = 5000

# Additional registry configuration to disable SSL
registry['enable'] = true
registry['registry_http_addr'] = "0.0.0.0:5000"
registry_nginx['ssl_certificate'] = false
registry_nginx['ssl_certificate_key'] = false

# Registry configuration for better compatibility with tunnels
registry['registry_http_addr'] = "0.0.0.0:5000"
registry['registry_http_relativeurls'] = false
registry['registry_http_draintimeout'] = "60s"
registry['registry_http_host'] = "https://registry-gitlab.dungxbuif.com"

# Storage configuration to handle blob uploads better
registry['storage_filesystem_rootdirectory'] = "/var/opt/gitlab/gitlab-rails/shared/registry"
registry['storage_cache_blobdescriptor'] = "inmemory"

# Health and debug configuration
registry['health_storagedriver_enabled'] = true
registry['log_level'] = "info"

# Disable redirect for better tunnel compatibility
registry['storage_redirect_disable'] = true

# Configure timeouts for large uploads
registry['http_timeout'] = "300s"
registry['http_idle_timeout'] = "300s"
registry['http_read_timeout'] = "300s"
registry['http_write_timeout'] = "300s"

# Fix for Docker registry retrying issues
registry['storage_delete_enabled'] = true
registry['storage_filesystem_maxthreads'] = 100

# Registry middleware configuration
registry['middleware_registry'] = [
  {
    'name' => 'cloudfront',
    'disabled' => false,
    'options' => {
      'baseurl' => 'https://registry-gitlab.dungxbuif.com',
      'privatekey' => '/dev/null',
      'keypairid' => 'none',
      'duration' => '3000s'
    }
  }
]

# Disable some problematic features for tunnel compatibility
registry['validation_disabled'] = true
registry['compatibility_schema1_enabled'] = true

