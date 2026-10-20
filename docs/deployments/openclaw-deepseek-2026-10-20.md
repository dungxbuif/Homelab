---
type: Deployment
title: "OpenClaw DeepSeek-V4.1-Flash provider verification"
description: "Production-safe verification of the existing OpenClaw DeepSeek provider on VM100"
timestamp: 2026-10-20T16:00:00+07:00
---

# OpenClaw DeepSeek-V4.1-Flash provider verification

## Scope

This change is limited to the production Swarm service `openclaw` on VM100.
Telegram, gateway routing, trusted proxies, Control UI origins, state volumes,
and all other homelab services remain unchanged.

## Intended configuration

- Provider: `fpt-deepseek`
- Base URL: `https://token-api.fpt.ai/v1`
- Default model: `fpt-deepseek/DeepSeek-V4.1-Flash`
- Credential source: runtime `OPENAI_API_KEY`; the secret value is not stored in
  this repository or printed in logs.

## Result

The live host and container already matched the intended configuration, so no
service restart or provider mutation was required. A timestamped backup of the
active `/opt/apps/openclaw/state/openclaw.json` was created before closing the
verification. The active task remained healthy.

## Verification

- Swarm service has one running task on `vm100-prod` and reports healthy.
- `openclaw models list --json` reports
  `fpt-deepseek/DeepSeek-V4.1-Flash` as available, configured and default.
- Gateway logs report `agent model: fpt-deepseek/DeepSeek-V4.1-Flash` and
  `gateway ready`.
- Telegram isolated polling started successfully.
- Credential presence was checked by metadata only; no secret value was
  emitted.

## Rollback

The backup made on VM100 under `/opt/apps/openclaw/backups/` is the rollback
source. Do not restore it without checking the current provider and model
catalog first.
