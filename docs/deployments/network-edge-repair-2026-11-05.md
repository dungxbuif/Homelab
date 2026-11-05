---
type: Deployment
title: Network edge repair — CouchDB LiveSync and RustDesk trace
generated:
  by: codex
  at: "2026-11-05T13:05:00+07:00"
stale_after: "2026-12-05T13:05:00+07:00"
lifecycle: active / RustDesk follow-up open
---

# Network edge repair — 2026-11-05

## CouchDB LiveSync

The NetBird VPN was already enabled on the workstation: `wt0` had
`100.69.32.183`, the `10.10.0.0/24` route was present, and Pi5 responded over
the mesh. The observed `403` was caused by live Pi5 Traefik drift: the
`sync-db` public router incorrectly had `lan-only` attached. The VPS/Rathole
source was therefore denied before CouchDB.

Only that middleware was removed. `couchdb.dungxbuif.com` was left LAN-only.
The live file was backed up before publication:

```text
/home/dungxbuif/edge/traefik/dynamic.yml.bak-20261105T060120+0000
```

Post-repair checks:

| Check | Result |
|---|---|
| Public anonymous `/` | `401` CouchDB `unauthorized` |
| Public anonymous `/obsidian_vault` | `401` CouchDB `unauthorized` |
| Authenticated `obsidian_vault` | `200` |
| Public LAN-only `couchdb.dungxbuif.com` | `403`, expected |

The route catalog and checked-in generated artifact already describe this
correct public/lan split; the live file was the stale copy.

## RustDesk

The local RustDesk client is running and uses
`rustdesk.dungxbuif.com:21116`. Its current connection log reports:
`Failed to connect to rustdesk.dungxbuif.com:21116: Please try later(115)`.
DNS resolves the hostname to the VPS `103.82.21.202`, but external TCP probes
to `21115`, `21116`, `21117`, `21118`, and `21119` are all refused. This proves
the failure is at the VPS `hbbs`/`hbbr` listener or provider firewall; it is
not a disabled VPN client.

No RustDesk server mutation was made because gateway SSH authorization is not
available in this environment. Required next action is a read-only VPS check
of `docker ps`, `ss -lntup`, `iptables`/provider firewall, then restart or
firewall repair only after the failing layer is confirmed.
