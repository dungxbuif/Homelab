# Temporary GitLab VPS HTTPS Route - 2026-09-15

## Decision and scope

The operator approved a temporary public GitLab HTTPS path while Orange Pi
`10.10.0.2:22` resets before SSH key exchange and new edge Swarm tasks remain
stuck at `Accepted`. At approval, public GitLab returned 404; internal VM100
GitLab HTTP and public SSH `:2222` were healthy. Do not restart or rewrite the
Orange Pi edge services, the VPS production Rathole `7000` tunnel, or the
separate Git SSH tunnel.

Deploy a **new isolated** Rathole HTTP server on VPS port `7002/tcp` for its
outbound VM100 client. The service endpoint `8085/tcp` is Docker-network-only
on VPS `gateway-network`, not a host-published port. A portless VM100 Swarm
client on `homelab-net` forwards to `tasks.gitlab_gitlab:80`; the VPS server
never joins the homelab overlay. Use the already pinned Rathole image digest,
a new per-service token, and Noise NK encryption. Keep server private key
and token in a mode-0600 VPS runtime file owned by image UID 1000; keep the
client token/public key in a Pi5 Swarm secret and ignored local credentials.
The external VPS static address is a justified tunnel-endpoint IP exception
because split DNS resolves the public gateway hostname to Orange Pi on LAN.

VPS Traefik v3.6 already has `providers.docker` enabled with
`exposedByDefault: false` and a Cloudflare DNS-01 `letsencrypt` resolver.
Attach the new server only to the VPS `gateway-network`; Compose labels
`traefik.enable=true`, `Host(gitlab.dungxbuif.com)`, `websecure`,
`tls.certresolver=letsencrypt`, and upstream port `8085` create its HTTPS
router. GitLab's existing term must be removed from the **VPS TCP TLS
passthrough rule**, because TCP routers precede HTTP routers on the same
entry point. No other HostSNI term, network, host port, or domain route may
change. The Orange Pi GitLab file route remains staged source only.

## Rollout and rollback

Record hashes and backup VPS `/root/gateway/dynamic.yml` before changing it.
Validate the proposed rule through a YAML parser and exact before/after
assertions; update the live bind-mounted file **in place** so Traefik's file
watcher sees the same inode. Do not replace/rename the file. Bring up the
new VPS Rathole server, verify its internal port and Docker labels, then
the VM100 client and its authenticated Noise control channel. Only then
remove the GitLab HostSNI term. Poll ACME issuance, public valid TLS,
`/users/sign_in` and page assets, and smoke-test pre-existing HTTPS domains
plus public Git SSH. A self-signed/default certificate, 404/502, or a
regression triggers restoring the **same VPS file in place** from backup and
removing only the new HTTP tunnel project/Swarm client. Do not touch the
database, GitLab data, existing SSH tunnel, or Orange Pi runtime.

This is temporary routing, not a label migration for Orange Pi. After SSH
admin access to Orange Pi is restored, apply its staged GitLab file router,
verify edge HTTPS, and cut GitLab back to passthrough before removing the
temporary HTTP tunnel. Record the final path and perform clone/push/pull,
backup/restore, and optional SMTP/S3 work separately.

## Verification boundaries

- Public DNS `gitlab.dungxbuif.com` resolves to VPS `103.82.21.202`.
- GitLab public HTTPS uses a valid certificate and login page responds 200.
- Public SSH `:2222` host key still matches GitLab's internal ED25519 key.
- Homepage, n8n, OpenClaw, MyPocket money, Family Tree, and RelayHub
  `/healthz` keep their expected responses.
- No VM100/Pi5 app host port or VPS HTTP backend host port is published.
- Public login page availability is **not** a clone/push/pull, account auth,
  CI, or backup/restore test.

## Public registration safety decision

After the temporary VPS route went live, a read-only GitLab Rails query
returned `signup_enabled=true`. The operator explicitly approved disabling
self-registration for this internal instance. Set only
`Gitlab::CurrentSettings.signup_enabled` to `false` through the supported
Rails application setting; preserve existing users and GitLab database
contents. Verify the setting returns `false` and the public sign-up page no
longer offers a registration form. Admin-created users remain possible.

## Executed outcome (2026-09-16)

The tunnel and VPS labeled HTTP router are live. During rollout, public
GitLab returned 200 through `gitlab-temp@docker` even before removal of the
old VPS TCP HostSNI term; the cause of this selection was not established.
The guarded cutover nevertheless removed that one term to leave an explicit
HTTP path. VPS host and Traefik-container dynamic YAML have the same SHA-256
`9daa3634c5f4f00d11627b118eb451aeeaefb845aa20f3c4c79579820c40fd5e`
and the same bind-mounted inode. Backup:
`/root/gateway/dynamic.yml.bak-gitlab-temp-20260915-171055-839423`.
Public login and CSS returned 200 with certificate verification, public
Git SSH key fingerprint remained unchanged, and the existing domain smoke
tests passed. GitLab `signup_enabled=false`; public sign-up redirects to
sign-in. Orange Pi direct GitLab 404 and its admin SSH fault remain. Account
authentication, repository operations, CI, and off-host backup/restore are
outside this verification.

## References

- [Traefik TCP versus HTTP router precedence](https://doc.traefik.io/traefik/v3.6/reference/routing-configuration/tcp/routing/router/)
- [Traefik Docker labels](https://doc.traefik.io/traefik/v3.6/reference/install-configuration/providers/docker/)
- [Traefik certificate resolver](https://doc.traefik.io/traefik/v3.6/reference/routing-configuration/http/tls/overview/)
- [Rathole Noise transport](https://github.com/rathole-org/rathole/blob/main/docs/transport.md)
