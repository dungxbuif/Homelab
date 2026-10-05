# GitLab Online Backup

`run-gitlab-backup.sh` runs on VM100 against the healthy GitLab Omnibus
container. It uses `gitlab-backup create` and `gitlab-ctl backup-etc` without
stopping, scaling, or recreating GitLab.

Each complete run contains:

- the native GitLab archive for database, repositories, uploads, artifacts,
  packages, LFS, Pages, and snippets as supported by the instance;
- the supported config/secrets archive, including `gitlab.rb` and
  `gitlab-secrets.json`;
- a separate online archive of the local filesystem Registry;
- a secret-free coverage manifest with GitLab and PostgreSQL versions;
- `checksums.sha256` and `COMPLETE`.

Redis cache, sessions, and Sidekiq queues are intentionally excluded. A
restore must load PostgreSQL globals first and use a compatible PostgreSQL
major. The current instance dumps from PostgreSQL 16.14 with the GitLab
container's PostgreSQL 17.10 client; a PostgreSQL 16 target needs the documented
`transaction_timeout` compatibility handling, while PostgreSQL 17 was used for
the isolated rehearsal.

The local Registry archive is required because it is filesystem-backed today.
If GitLab later moves any storage to RustFS or another object store, that store
becomes an additional required backup class.
