---
type: Service
title: NetBird
description: Self-hosted NetBird management server and dashboard (stack netbird) on VM100; relay/STUN on the VPS
generated:
  by: claude-code/opus-5.5
  at: "2026-10-31T15:00:00+07:00"
stale_after: "2027-01-29T15:00:00+07:00"
lifecycle: active
class: internal
owner: dungxbuif
deployed_revision: server 0.82.0 / dashboard v2.96.0
---

# NetBird

## Summary

Private mesh VPN for admin access to the lab (replaced Headscale, Tailscale
and WireGuard admin access). Third-party app; class `internal` (unverified
intake), status `active`.

## Source

| Field | Value |
|---|---|
| Upstream | https://github.com/netbirdio/netbird, https://github.com/netbirdio/dashboard |
| Pinned version | `ghcr.io/netbirdio/netbird-server:0.82.0@sha256:7b5b53b2…`; `netbirdio/dashboard:v2.96.0@sha256:340b13c0…` |
| Deploy source | Swarm stack `netbird` (stack label still says `:latest` → image was updated by hand after deploy); stack file location in `homelab-ops` (unverified) |

## Internal architecture

`netbird-server` (management + signal, embedded relay off) and the
`netbird-dashboard` UI on VM100. Relay and STUN run on the VPS as the
`netbird-relay` Compose project (TCP 443 via HostSNI, UDP 3478);
`netbird-relay.dungxbuif.com` resolves to the VPS from LAN DNS too.

## Runtime

| Field | Value |
|---|---|
| Host / placement | VM100 (`node.hostname == vm100-prod`) |
| Services | `netbird_netbird-server`, `netbird_netbird-dashboard` |
| Domain / exposure | `netbird.dungxbuif.com` (public, required for remote peers) |
| Networks | server: `netbird-net`, `edge-http-net`, `pg-net`; dashboard: `netbird-net`, `edge-http-net` |
| Limits | server 1 CPU / 1 GiB; dashboard 0.5 CPU / 512 MiB |
| Healthcheck | none on either service |
| Update | `failure_action: rollback` |

## Data

| Store | Name | Backup class | Last restore evidence | RPO / RTO |
|---|---|---|---|---|
| PostgreSQL (Pi5, `pgbouncer:6432`) | `netbird`, `netbird_activity`, `netbird_idp` | Databasus → Google Drive | automatic restore verification passed 2026-10-31 | not stated |
| Config | `/opt/apps/netbird/config.yaml` (bind) | none | none | not stated |
| Volume | `netbird_netbird_data` → `/var/lib/netbird` | none | none | not stated |

## Secrets

No Swarm secrets. Server secrets live in `config.yaml` on VM100; dashboard
gets `AUTH_CLIENT_SECRET` etc. as env vars. 1Password paths (unverified).

## Delivery

- Manual image updates from the Pi5 ([version-upgrade-2026-10-31](../deployments/version-upgrade-2026-10-31.md)).
- Rollback: `docker service rollback` on both services; config file and volume
  are not versioned.

## Operations

- Health: dashboard `https://netbird.dungxbuif.com/` loads and peers connect (no probe)
- Logs: `docker service logs netbird_netbird-server` (Pi5)
- Known issue: if NetBird is down, remote admin access depends on LAN; keep a
  LAN path to the Pi5.

## Gate status

| Gate | State | Evidence / exception (expiry) |
|---|---|---|
| G0 Intake | fail | no `app.yml` |
| G1 Build | partial | upstream images pinned by digest |
| G2 Security | not assessed | secrets in config file/env |
| G3 Runtime | fail | stack drifted from file; no healthchecks |
| G4 Data | partial | DBs restore-verified; config/volume not backed up |
| G5 Observability | not assessed | |
| G6 Release | not assessed | |
| G7 Docs | partial | this doc |
| G8 Operate | not assessed | |

## Recent changes

- 2026-10-31: server `0.82.0`, dashboard `v2.96.0` applied.
- 2026-10-31: three NetBird DBs enrolled in Databasus restore verification.
