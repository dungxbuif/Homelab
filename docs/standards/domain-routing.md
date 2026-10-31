---
type: Standard
title: "Domain Routing"
description: "Add, rename and remove domains for apps from one declaration, published to the Pi5 edge and the VPS gateway with verification and automatic rollback"
status: draft
generated:
  by: claude-code/opus-5.5
  at: 2026-10-31T19:30:00+07:00
stale_after: 2027-01-29T19:30:00+07:00
tags: [dns, traefik, gateway, routing]
---

# Domain Routing

**Today:** adding a domain means hand-editing the Pi5 Traefik file `dynamic.yml` and, for public names, the VPS HostSNI list in `/root/gateway/dynamic.yml`. DNS needs no change: Cloudflare has the wildcard `*.dungxbuif.com → 103.82.21.202`, and the Pi5 AdGuard rewrites `*.dungxbuif.com → 10.10.0.5` (both verified on 2026-10-31).

## 1. One declaration

```yaml
# homelab-ops/stacks/<app>/app.yml
domains:
  - host: notes.dungxbuif.com
    exposure: public          # public | lan | private
    service: web
    port: 8080
    paths: ["/"]
    redirect_from: [old-notes.dungxbuif.com]   # 301 kept for 30 days
```

Routes that do not belong to an app (couchdb, llm, gitlab, …) live in `routes/catalog.yml` and use the same schema.

## 2. Generated outputs

| Output | When |
|---|---|
| Pi5 Traefik router + service (`generated/pi5-traefik.yml`). `lan`/`private` get the `lan-only` middleware | Every domain |
| VPS HostSNI allow-list (`generated/vps-hostsni.yml`). Names not on the list are refused even though the wildcard resolves | `public` only |
| Cloudflare record (tofu `dns`) | Only exceptions to the wildcard (for example `netbird-relay`) |
| AdGuard rewrite | Only exceptions (names that must resolve to the VPS) |
| NetBird DNS | `private` |
| Blackbox targets (LAN path + public path) | Every domain |

TLS: one wildcard certificate on Pi5 through Cloudflare DNS-01. The DNS-edit token lives in 1Password.

## 3. MR checks

The schema is valid. The host is unique. The upstream exists in `stacks/`. Exposure matches the class (a `lab` app cannot be `public`). A readable diff is commented on the MR.

## 4. Add (in order)

1. The app is deployed and healthy. No route is published without a healthy app.
2. **Pi5:** write the route file in place (the inode is kept for the bind mount) → Traefik hot-reloads → the router appears in the Traefik API → LAN curl through `10.10.0.5`.
3. **VPS** (`public` only, manual job): back up → write → the router appears → public curl. On any failure, **restore the previous file automatically**.
4. Monitoring target on → doc-bot updates the vault → Mezon.

`lan` and `private` publish automatically after merge. `public` needs a click on step 3.

## 5. Remove and rename

**Remove** runs in reverse order:
1. Take the name off the VPS HostSNI list → public is refused.
2. Remove the Pi5 router → LAN returns 404.
3. Monitoring off → vault and log updated.

**Rename** = add the new name, keep a 301 from the old one for 30 days, then remove the old one automatically.

## 6. Publish safety

- Before writing, the hash of the live file is compared with the last applied version. A mismatch means a manual edit: stop and alert, never overwrite.
- Every publish takes a timestamped backup and rolls back automatically.
- On the VPS, the `automation` key is restricted with `command=` to a single `gateway-publish` wrapper. It reads the file on stdin, validates it, swaps it and rolls back on failure. No root shell.
- The nightly drift check compares the live routes on both edges with the generated files.

## 7. Migration (plan P3)

1. Model the existing 28 routes until the generated file is byte-identical to the live one.
2. Switch the source of truth to the generated file. Remove `migration/traefik/dynamic.yml`, `vps-hostsni-edit.py` and `edge-publish.sh`.
3. Install `gateway-publish` on the VPS and move TLS to the wildcard DNS-01 certificate.
