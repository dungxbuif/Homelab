external_url 'https://gitlab.dungxbuif.com'

letsencrypt['enable'] = false
nginx['listen_port'] = 80
nginx['listen_https'] = false

postgresql['enable'] = false
gitlab_rails['db_adapter'] = 'postgresql'
gitlab_rails['db_encoding'] = 'unicode'
gitlab_rails['db_database'] = 'gitlabhq_production'
gitlab_rails['db_username'] = 'gitlab'
gitlab_rails['db_host'] = 'postgres'
gitlab_rails['db_port'] = 5432
gitlab_rails['db_password'] = File.read('/run/secrets/gitlab_db_password').strip

redis['enable'] = false
gitlab_rails['redis_host'] = 'redis-prod'
gitlab_rails['redis_port'] = 6379
gitlab_rails['redis_database'] = 2
gitlab_rails['redis_password'] = File.read('/run/secrets/gitlab_redis_password').strip

gitlab_rails['initial_root_password'] = File.read('/run/secrets/gitlab_root_password').strip
gitlab_rails['gitlab_shell_ssh_port'] = 2222
gitlab_rails['smtp_enable'] = false

puma['worker_processes'] = 2
sidekiq['max_concurrency'] = 10
prometheus['enable'] = false
registry_external_url 'https://registry-gitlab.dungxbuif.com'
registry['enable'] = true
registry['database']['enabled'] = false
registry_nginx['listen_port'] = 5005
registry_nginx['listen_https'] = false
registry_nginx['redirect_http_to_https'] = false
gitlab_pages['enable'] = false
gitlab_kas['enable'] = false
