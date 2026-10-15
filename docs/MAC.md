---
type: Reference
title: "Mac Mini Runtime Dependencies"
description: "Specification of Mac mini services that remain after VM100 production migration"
timestamp: 2026-09-16T00:00:00+07:00
---

# Mac Mini Runtime Dependencies

> **Host:** Mac mini (Apple Silicon, arm64) — active LAN IP `10.10.0.6`
> while Ethernet `10.10.0.10` is unplugged; public OCR/LLM now use the
> Mac Rathole client so the Mac can move outside the LAN.
> **Role:** Provides native OCR and local LLM dependencies.
> Most user-facing production web apps moved to VM100 on 2026-09-11.
> **Stack root:** `~/production/` (`/Users/dungxbuif/production/`).

## Current Role

The Mac is no longer the primary home production compute node for homepage,
OCR proxy, Family Tree, or MezonHook. Those services now run on VM100
(`10.10.0.31`), with the current Pi5 edge routing to VM100.

The Mac still provides:

| Runtime | Address | Used by | Status |
|---|---|---|---|
| Native OCR app | Outbound WSS/HTTPS to `ocr.dungxbuif.com`; no local OCR listener | VM100 multi-node `macocr-proxy` | Universal manually shared app, host fingerprint, shared Bearer key; node/routing visible to admin |
| LM Studio | Mac host port `1234`; public via VPS `:18123` | `llm.dungxbuif.com` | active dependency; tunnel ready, backend must be running |
| MyPocket development checkout | `/Users/dungxbuif/workspace/MyPocket/` | Local development | Source intentionally unmoved; production web/API/worker are on VM100; local dev container health not audited here |

GoClaw is intentionally not public-routed in the current topology. Its previous
`goclaw.dungxbuif.com` Traefik router was removed on 2026-09-11 pending a new
operator plan.

## Current Routing

```text
Internet -> VPS gateway-traefik -> Rathole -> Pi5 edge-traefik-pi5
  -> tasks.homepage:80       homepage (Swarm overlay)
  -> tasks.mezonhook:8080    MezonHook (Swarm overlay)
  -> tasks.family-tree:3000  Family Tree (Swarm overlay)
  -> tasks.macocr-proxy:8080 <- outbound WSS/443 <- Mac OCR apps (LAN or roaming)
  -> VPS :18123 -> Mac Rathole client -> host.docker.internal:1234 LM Studio
```

`money.dungxbuif.com` now routes to VM100 `tasks.mypocket-web:80`.
MyPocket production API/worker use Pi5 PgBouncer and Redis DB1 via Docker DNS.
Keeping its dev checkout outside the Homelab infrastructure repo does not mean its
production runtime stayed on the Mac.

## Mac Service Tunnel

The deployed roaming path is a local Docker Compose Rathole client at
`/Users/dungxbuif/dev-env/mac-service-tunnel`. It dials the VPS shared
Rathole server and retains only the LLM backend mapping after the OCR cutover on 2026-10-06:

- `mac-llm`: VPS `103.82.21.202:18123` -> Mac `host.docker.internal:1234`

Pi5 Traefik routes `ocr.dungxbuif.com` to VM100 `macocr-proxy`; Mac OCR apps now connect directly to this public domain using WSS. The old app was removed from `/Users/dungxbuif/Applications/Mac OCR Native.app`; the operator then installed the final 2.0.0 (build 7) DMG at `/Applications/Mac OCR Native.app`. TCP 8787 remains closed. The manual Universal build is retained under `/Users/dungxbuif/workspace/mac-ocr/native/dist/` as an app, ZIP, and DMG. Pi5 Traefik routes
`llm.dungxbuif.com` directly to the LLM VPS listener. The Rathole token lives
only in the Mac-local `.env` and rendered runtime config; do not commit either
file.

NetBird remains useful for private administration, SSH, and private backend
DNS/ACLs, but it is not required for the public OCR/LLM route above.

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
cd /Users/dungxbuif/dev-env/mac-service-tunnel
docker compose up -d
docker logs mac-service-tunnel --tail 80

# Local dependency probes on the Mac
curl -fsS https://ocr.dungxbuif.com/healthz
curl -sS http://127.0.0.1:1234/v1/models

# Public route probes
curl -sS https://ocr.dungxbuif.com/
curl -sS https://llm.dungxbuif.com/v1/models
```
