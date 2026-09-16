---
type: Reference
title: "Mac Mini Runtime Dependencies"
description: "Specification of Mac mini services that remain after VM100 production migration"
timestamp: 2026-09-16T00:00:00+07:00
---

# Mac Mini Runtime Dependencies

> **Host:** Mac mini (Apple Silicon, arm64) — active LAN IP `10.10.0.6`
> while Ethernet `10.10.0.10` is unplugged.
> **Role:** Provides native OCR and local LLM dependencies.
> Most user-facing production web apps moved to VM100 on 2026-09-11.
> **Stack root:** `~/production/` (`/Users/dungxbuif/production/`).

## Current Role

The Mac is no longer the primary home production compute node for homepage,
OCR proxy, Family Tree, or MezonHook. Those services now run on VM100
(`10.10.0.31`), with Orange Pi `edge_traefik` routing to VM100.

The Mac still provides:

| Runtime | Address | Used by | Status |
|---|---|---|---|
| Native OCR engine | `10.10.0.6:8787` | VM100 `macocr-proxy` | active dependency |
| LM Studio | `10.10.0.6:1234` | `llm.dungxbuif.com` | active dependency |
| MyPocket development checkout | `/Users/dungxbuif/workspace/MyPocket/` | Local development | Source intentionally unmoved; production web/API/worker are on VM100; local dev container health not audited here |

GoClaw is intentionally not public-routed in the current topology. Its previous
`goclaw.dungxbuif.com` Traefik router was removed on 2026-09-11 pending a new
operator plan.

## Current Routing

```text
Internet -> VPS gateway-traefik -> Rathole -> Orange Pi edge_traefik
  -> tasks.homepage:80       homepage (Swarm overlay)
  -> tasks.macocr-proxy:8080 macocr-proxy (Swarm overlay)
  -> tasks.mezonhook:8080    MezonHook (Swarm overlay)
  -> tasks.family-tree:3000  Family Tree (Swarm overlay)
  -> 10.10.0.6:1234    LM Studio
```

`money.dungxbuif.com` now routes to VM100 `tasks.mypocket-web:80`.
MyPocket production API/worker use Pi5 PgBouncer and Redis DB1 via Docker DNS.
Keeping its dev checkout outside `homelab/projects/` does not mean its
production runtime stayed on the Mac.

## Proposed Roaming Backend (not deployed)

The operator wants to move the Mac outside the LAN while continuing to serve
OCR/LLM. The proposed direction is NetBird agents on Mac and the consuming
homelab host, with stable private backend DNS and narrow ACLs for TCP
`8787/1234`. At home, keep LAN `10.10.0.6` for management; application
upstreams would use the private overlay name both at home and remotely.

No agent enrollment, backend domain, ACL, DNS switch, or upstream change was
performed. Current source still depends on the LAN IP. NetBird dashboard
availability does not prove relay/STUN connectivity or container routing.
Before moving the Mac, verify peer access, DNS from consuming containers,
app listen interfaces, API auth, sleep/wake reconnect, and relay fallback.
Do not public-expose native OCR/LM Studio as a shortcut.

## Historical Notes

The previous Mac Docker production stack contained:

- `homelab-homepage`
- `homelab-macocr-proxy`
These containers were stopped and removed after VM100 cutover so the services do
not run twice. OmniScan bot and GoClaw runtime data were removed.

## Operations

Use this file for Mac dependency checks only. VM100 service operations are in
[VM100.md](./VM100.md).

```bash
# Native dependency probes from another LAN host
curl -sS http://10.10.0.6:8787/capacity
curl -sS http://10.10.0.6:1234/v1/models
```
