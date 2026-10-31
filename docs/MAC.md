---
type: Reference
title: "Mac Mini Runtime Dependencies"
description: "Mac mini native OCR and LLM dependencies that remain after the VM100 migration"
timestamp: 2026-10-31T00:00:00+07:00
---

# Mac mini — native dependencies

> **Not audited live on 2026-10-31.** Facts below are from earlier records and
> are (unverified) unless a VPS-side check confirms them.

| Field | Value |
|---|---|
| Hardware | Mac mini, Apple Silicon (arm64) |
| LAN IP | `10.10.0.6` Wi-Fi; Ethernet `10.10.0.10` when plugged (unverified) |
| Role | Native OCR worker and LM Studio; no production web apps (all on VM100) |

## What runs on the Mac

| Runtime | Path / address | Used by |
|---|---|---|
| Mac OCR Native 2.0.0 (build 7) | `/Applications/Mac OCR Native.app`; dials out WSS/443 to `ocr.dungxbuif.com`; no local listener (TCP 8787 closed) | VM100 `macocr-proxy` |
| LM Studio | `127.0.0.1:1234` | `llm.dungxbuif.com` |
| Mac service tunnel | Docker Compose Rathole client at `/Users/dungxbuif/dev-env/mac-service-tunnel`; single mapping `mac-llm`: VPS `103.82.21.202:18123` → `host.docker.internal:1234` | Pi5 Traefik routes `llm.dungxbuif.com` to the VPS listener |

The VPS audit (2026-10-31) confirms the shared Rathole server still listens on
`18123`. The Rathole token lives only in the Mac-local `.env` and rendered
config; never commit either. OpenClaw and Whiteboard no longer use LM Studio
(they use the FPT DeepSeek endpoint), so LM Studio's remaining consumers are
(unverified). The universal OCR build artifacts are kept in
`/home/dungxbuif/workspace/projects/mac-ocr/native/dist/`.

NetBird is used for private admin/SSH; it is not required for the OCR/LLM
public paths.

## Operations

```bash
cd /Users/dungxbuif/dev-env/mac-service-tunnel
docker compose up -d
docker logs mac-service-tunnel --tail 80

curl -sS http://127.0.0.1:1234/v1/models         # LM Studio local
curl -fsS https://ocr.dungxbuif.com/healthz       # OCR proxy
curl -sS https://llm.dungxbuif.com/v1/models      # public LLM route
```

Rollback: stop the tunnel (`docker compose down`) to withdraw the LLM route;
OCR keeps working as long as the app can reach `ocr.dungxbuif.com`.
