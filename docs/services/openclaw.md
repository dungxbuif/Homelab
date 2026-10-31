---
type: Service
title: OpenClaw
description: OpenClaw AI agent gateway (Telegram bot), locally built image as a Swarm service on VM100 at openclaw.dungxbuif.com
generated:
  by: claude-code/opus-5.5
  at: "2026-10-31T15:00:00+07:00"
stale_after: "2027-01-29T15:00:00+07:00"
lifecycle: active
class: internal
owner: dungxbuif
deployed_revision: "homelab/openclaw:vm100-20260912"
---

# OpenClaw

## Summary

Personal AI agent gateway reachable through Telegram and a web gateway.
Third-party app; class `internal` (unverified intake), status `active`.

## Source

| Field | Value |
|---|---|
| Upstream | OpenClaw, https://github.com/openclaw/openclaw (unverified exact upstream ref) |
| Pinned version | **`homelab/openclaw:vm100-20260912`, built locally on VM100** — no registry, no digest, upstream commit not recorded |
| Deploy source | none: `docker service create`, no stack in `homelab-ops`; build recipe location (unverified) |

## Internal architecture

Gateway on `:18789`. LLM provider `fpt-deepseek` (OpenAI-compatible
`https://token-api.fpt.ai/v1`, model `DeepSeek-V4.1-Flash`); Telegram in
polling mode; `trustedProxies` include the Pi5 edge. It no longer uses LM
Studio. Possible CouchLoom MCP client (not verified, see [CouchLoom](./couchloom.md)).

## Runtime

| Field | Value |
|---|---|
| Host / placement | VM100 (`node.hostname==vm100-prod`); local image pins it there |
| Service | `openclaw` |
| Domain / exposure | `openclaw.dungxbuif.com` → `tasks.openclaw:18789` (exposure unverified) |
| Networks | `edge-http-net` |
| Limits | 1 CPU / 2 GiB; no reservations |
| Healthcheck | `node dist/docker-healthcheck.js` |
| Update | `failure_action: rollback` |

## Data

| Store | Name | Backup class | Last restore evidence | RPO / RTO |
|---|---|---|---|---|
| Bind mounts | `/opt/apps/openclaw/{state,workspace,auth-profile-secrets}` (VM100) | none | none | not stated |

## Secrets

Plain env vars, not Swarm secrets: `OPENCLAW_GATEWAY_TOKEN`,
`TELEGRAM_BOT_TOKEN`, `OPENAI_API_KEY`. Auth profiles in the bind-mounted
`auth-profile-secrets` dir. 1Password paths (unverified).

## Delivery

- Manual: build on VM100, tag `vm100-<date>`, `docker service update --image`.
- Rollback: `docker service rollback openclaw` (only works while the old
  local image still exists on VM100).

## Operations

- Health: container healthcheck; URL `https://openclaw.dungxbuif.com/`
- Logs: `docker service logs openclaw` (Pi5)
- Known issue: if VM100 image cache is pruned, the service cannot restart.

## Gate status

| Gate | State | Evidence / exception (expiry) |
|---|---|---|
| G0 Intake | fail | no `app.yml` |
| G1 Build | fail | local-only image, no registry/digest ([registry standard](../standards/registry.md)) |
| G2 Security | fail | tokens and API key in env vars |
| G3 Runtime | fail | `docker service create`, no stack |
| G4 Data | fail | state not backed up |
| G5 Observability | not assessed | |
| G6 Release | not assessed | |
| G7 Docs | partial | this doc |
| G8 Operate | not assessed | |
