# GitLab Container Registry trial - 2026-09-16

## Intent and decision

The operator approved trying GitLab Container Registry before replacing the
existing Pi5 `docker-registry`. Keep Pi5 registry, its storage, auth, and
`registry.dungxbuif.com` route unchanged. Use a separate trial domain
`registry-gitlab.dungxbuif.com` that resolves to the VPS publicly; internal
split DNS resolves it to Orange Pi, so public client tests must explicitly
target the VPS until an edge route is live.

GitLab CE 18.11.11 on VM100 will run its bundled registry with filesystem
storage under its existing `/var/opt/gitlab` bind mount. For this narrow
trial, disable the optional registry metadata database; adding a second DB
and testing RustFS compatibility are separate changes. Set
`registry_external_url` to the trial HTTPS domain, terminate TLS on VPS
Traefik, and make GitLab's registry NGINX listen on private HTTP port 5005.
The GitLab service remains portless on `homelab-net`.

Use a new isolated Noise Rathole project: VM100 client forwards Docker DNS
`tasks.gitlab_gitlab:5005` to a VPS server. Only authenticated control
`7003/tcp` is host-published; backend `8086/tcp` is private to VPS Docker
`gateway-network`. Traefik Docker labels route only the trial domain over
HTTPS. Do not alter the existing GitLab web/SSH tunnels, VPS shared TCP
passthrough rule, Orange Pi service, or Pi5 registry. This is a trial, not
a production registry cutover.

## Deployment and verification

1. Confirm VM100 storage and Pi5 DB capacity; take a timestamped VM100
   config/data snapshot and Pi5 `gitlabhq_production` database dump. Record
   restore locations without logging credentials. Validate source Ruby,
   Compose, Swarm stack, TOML templates, and free ports.
2. Generate a separate Noise token/keypair outside the repo and deploy only
   the isolated VPS server/client. Apply the Omnibus registry change to
   GitLab with a **non-overlapping** replacement task: scale GitLab to zero,
   wait for the old task to exit, update its Swarm config, then scale to one.
   The new stack uses versioned Swarm config
   `gitlab_omnibus_registry_trial_20260916` because configs are immutable.
   Expect a short GitLab web/SSH interruption during reconfiguration.
3. Verify GitLab health, `/v2/` 401 challenge and token realm, valid public
   TLS, existing web/SSH routes, and Pi5 registry health. Create a
   disposable GitLab project; authenticate with a scoped credential (or
   root for this isolated test), push/pull an image by digest/tag, and
   compare digest. No CI/Swarm pull migration until that succeeds.
4. Reconcile this note and the GitLab human/agent-readable runbook with the
   observed result, resource impact, and rollback boundary.

## Rollback and boundaries

If GitLab health or the existing routes regress, disable the trial route
and restore the previous GitLab Omnibus config through a non-overlapping
task replacement. Keep the backup DB/config/data and do not delete the
Pi5 registry. Trial image/project cleanup is separate from recovering
GitLab. A registry backup must account for image storage; a DB dump alone
does not preserve layers. Large-image upload behavior, garbage collection,
metadata DB, RustFS/S3, deploy-token automation, and CI integration remain
untested until explicitly verified.

## Executed result (2026-09-16)

- Prechange backups: Pi5
  `/ssd-data/infra/gitlab/backups/registry-trial-before-20260916.dump`
  (`pg_restore -l` verified) and
  `/ssd-data/infra/gitlab/backups/omnibus-before-registry-trial-20260916.rb`;
  VM100 `/opt/apps/gitlab-snapshots/registry-trial-before-20260916.tgz`
  (tar listing verified). These are local snapshots, not a restore drill.
- The new server/client established a Noise control channel. VPS only
  publishes `7003`; Docker-private backend is `8086`. GitLab was scaled
  to zero, the old container disappeared, then the versioned-config stack
  started one replacement. The new GitLab task is healthy; registry runit
  process is running and private NGINX `:5005/v2/` returns 401.
- Trial HTTPS `/v2/` returns 401 with valid TLS and Bearer realm
  `https://gitlab.dungxbuif.com/jwt/auth`. `root/registry-trial` was created
  private. An ephemeral Pi5 OCI client authenticated with the root password
  read from a mode-0600 file via `--password-stdin`, pushed
  `smoke:20260916` (arm64), and copied it back into an OCI layout. Blob
  `sha256:e001ca9bbec820ee2d710e0540e20b71663ef5120d33897f500911d0231b432d`
  and config
  `sha256:6df9636795d37473994366014c25264edeb6c00d7a57188ff62d5a94276b4297`
  matched on push and pull. A separate `smoke-amd64:20260916` push and
  remote inspect reported `linux/amd64`; it was not pulled/run by VM100.
- One-time GitLab backup
  `/opt/apps/gitlab/data/backups/1789494830_2026_09_15_18.11.11_gitlab_backup.tar`
  completed and contains `registry.tar.gz` with trial manifest/layer paths,
  along with DB and repository inputs. GitLab config/secrets were not in
  that archive; separate VM100
  `/opt/apps/gitlab-snapshots/registry-trial-after-config-20260916.tgz`
  was created and listing-checked. Neither backup is scheduled/off-host,
  and no restore was attempted.
- During GitLab task replacement, the registry tunnel briefly returned 502
  because the client could not resolve `tasks.gitlab_gitlab`; a disposable
  Swarm DNS probe later resolved the new task address and `/v2/` stabilized
  at 401 without a config change. The probe was removed. Existing GitLab
  login 200, Git SSH fingerprint, n8n health 200, Pi5 registry `/v2/` 401,
  and disabled public sign-up (302 to sign-in) passed after replacement.
- VM100 idle sample: GitLab 3.187 GiB/10 GiB, trial client 3.613 MiB/128
  MiB; 10 GiB available RAM, 130 GiB free root. VPS trial server 3.566
  MiB/128 MiB. This is not sustained push/pull capacity telemetry.
- Post-replacement `gitlab:check SANITIZE=true` finished successfully:
  Shell/internal API, Gitaly, Sidekiq, Redis, migrations, permissions,
  hashed storage, and project namespace checks passed.
- A Pi5 read-only query against the administrative `postgres` database
  emitted a collation-version mismatch warning. The GitLab database query
  and dump completed; the warning belongs to a separate PostgreSQL
  maintenance audit and was not changed during this trial.

## Cutover gate

**Do not retire Pi5 `docker-registry` yet.** Lab split DNS still sends
`registry-gitlab.dungxbuif.com` to Orange Pi, whose direct trial route is
not deployed; the smoke client used temporary host overrides only inside
its disposable container. Native Docker daemon/Swarm pull on Pi5 and VM100,
CI credentials, deploy tokens, multiarch manifest lists, large uploads,
retention/garbage collection, automated off-host backup, and restore are
not verified. Fix Orange Pi admin SSH/edge routing (or approve a deliberate
alternate internal DNS route), then test native Docker and Swarm image pull
before moving tags or deleting the old registry.

## References

- [GitLab bundled registry configuration](https://docs.gitlab.com/administration/packages/container_registry/)
- [Registry metadata database modes](https://docs.gitlab.com/administration/packages/container_registry_metadata_database/)
- [Registry authentication and scopes](https://docs.gitlab.com/user/packages/container_registry/authenticate_with_container_registry/)
- [GitLab backup scope](https://docs.gitlab.com/administration/backup_restore/backup_gitlab/)
