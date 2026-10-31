---
type: Playbook
title: "System Ingress & Service Export"
description: "Current ingress topology, address plan, VPS layout, service export procedure and known pitfalls"
timestamp: 2026-10-31T12:00:00+07:00
---

# Ingress, Addresses and Service Export

Current as of 2026-10-31. Workload inventory is in [STACK.md](./STACK.md);
this page covers how traffic gets in and how to publish a service.

## Ingress paths

```text
Shared HTTPS:  VPS gateway-traefik (HostSNI allow-list) -> rathole-server :7000
               -> edge-rathole-pi5 -> edge-traefik-pi5 (TLS, Cloudflare DNS-01 wildcard)
               -> http://tasks.<service>:<port> on Swarm overlays
GitLab web:    VPS Traefik (TLS on VPS, Docker labels) -> Rathole 7002 -> VM100 client -> GitLab :80
Registry trial: VPS Traefik -> Rathole 7003 -> VM100 client -> GitLab :5005
Git SSH:       VPS :2222 -> Rathole 7001 -> VM100 client -> GitLab :22
NetBird relay: VPS TCP 443 HostSNI netbird-relay.dungxbuif.com; STUN UDP 3478
LLM:           VPS :18123 -> Mac Rathole client -> LM Studio :1234
OCR:           Mac worker -> outbound WSS/443 -> ocr.dungxbuif.com -> macocr-proxy
LAN DNS:       edge-adguardhome-pi5: *.dungxbuif.com -> 10.10.0.5;
               netbird-relay.dungxbuif.com -> 103.82.21.202
```

Pi5 also runs native `cloudflared` 2026.10.7, but it is degraded
(`Unauthorized: Tunnel not found`) and carries no accepted route.

## Address plan

| Device | Address | Role |
|---|---|---|
| Viettel modem | — | Bridge mode, VLAN 35, Wi-Fi off |
| MikroTik hEX S | `10.10.0.1` | PPPoE, NAT, DHCP, LAN routing |
| Orange Pi Zero 3 | `10.10.0.2` | Down; no role (see MikroTik DNS warning in [STATUS](./STATUS.md)) |
| Pi5 | `10.10.0.5` | Edge, Swarm manager, datastores |
| Mac mini | `10.10.0.6` | OCR worker, LM Studio |
| Proxmox | `10.10.0.20` | Hypervisor |
| VM100 | `10.10.0.31` | Production compute |
| VM110 | `10.10.0.32` | db-management worker |
| VPS | `103.82.21.202` | Public boundary |
| Mesh Wi-Fi | DHCP | AP/bridge mode |

## VPS layout (`/root`)

```text
gateway/                 gateway-traefik + rathole-server; dynamic.yml (HostSNI list), rathole.toml
gitlab-ssh-tunnel/       :2222 / :7001
gitlab-https-tunnel/     :7002, Docker-private :8085
gitlab-registry-trial/   :7003, Docker-private :8086
netbird-relay/           relay + STUN
rustdesk/                hbbs/hbbr, data in /root/rustdesk/data; WebSocket 21118-21119 blocked by firewall unit
coturn                   TCP/UDP 5349 (location unverified)
backup-bds/              retained Batdongsan SQL snapshot (unverified still present)
```

## Publishing an HTTP service

1. **Run it portless.** VM100: Swarm service on the right overlay (at least
   `edge-http-net` or `homelab-net`), placed on VM100, verify task health.
   Pi5: only approved datastore/infra services, no new host port.
2. **Route on Pi5.** Add a router/service to the file provider
   (`/home/dungxbuif/edge/traefik/dynamic.yml`; source in
   `homelab-ops/migration/traefik/dynamic.yml`) with upstream
   `http://tasks.<service>:<port>`. Never point at a LAN IP. Use the
   `lan-only` middleware for internal names.
3. **Publish on VPS** (public names only). Add the hostname to the HostSNI
   rule in `/root/gateway/dynamic.yml`. Back up and validate before reload; a
   bad edit takes down all public routes.
4. **DNS.** `*.dungxbuif.com` in Cloudflare already points at the VPS; add an
   explicit record only if needed.
5. **Verify** via LAN and via the public path, then record the change.

Do not use `edge-registrar/scripts/edge-publish.sh` (targets the retired Caddy
edge). Route and HostSNI edits are manual until the IaC plan renders them
from a catalog.

## Known pitfalls

- **Passwords with `/` in URLs** break Go `net/url` and exporter DSNs:
  URL-encode (`%2F`) in `DATABASE_URL`/`DATA_SOURCE_NAME`.
- **Recreating `redis-prod` from the base Compose only** drops its overlay
  attachments and breaks GitLab/MyPocket DNS. Always include the override;
  see [gitlab-redis-network runbook](./runbooks/gitlab-redis-network.md).
- **Fixed container names** block Compose recreate; rename the old container
  for rollback first.
- **Docker Desktop on macOS** `network_mode: host` cannot reach Mac-native
  services; use bridge plus `host.docker.internal:host-gateway`.
- **ISP throttles high-volume UDP**; public ingress deliberately uses TCP
  Rathole.
- **Docker Hub 429s** happen; pull exact candidates before a change window.

## Guardrails for agents

1. Pi5 images `linux/arm64`; VM100/VM110 `linux/amd64`.
2. No new host ports; route through Pi5 Traefik over overlays.
3. Pin image tags/digests. Floating tags still in use: AdGuard `latest`,
   PgBouncer `latest`, Family Tree `oven/bun:1-slim`, netbird-relay and
   RustDesk `latest`.
4. `mac-ocr` source is read-only; apply behaviour changes at build time.
5. VM100 and VM110 are production; nothing on Proxmox is disposable.
