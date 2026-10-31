---
type: Project
title: Mac OCR (OCR Platform)
description: "API-first OCR/scan platform: Go proxy on VM100 Swarm at ocr.dungxbuif.com, Apple Vision workers in a native Mac app"
generated:
  by: claude-code/opus-5.5
  at: "2026-10-31T18:00:00+07:00"
stale_after: "2027-01-29T18:00:00+07:00"
lifecycle: active
project: mac-ocr
class: public
owner: dungxbuif
repo: dungxbuif/mac-ocr
deployed_revision: "image scan-api-20261008 (built 2026-10-08 13:29 +07 from a working tree before 4810527; exact sha unverified)"
---

# Mac OCR (OCR Platform)

## Summary

Asynchronous OCR and document-scan API (REST, SSE, signed webhooks, MCP) with
an admin dashboard and Docusaurus docs embedded in one Go binary. Recognition
runs on the Mac mini in the native "Mac OCR Native" app (Apple Vision), which
dials **out** to the proxy over WSS, so the Mac needs no inbound port. Used by
MyPocket receipt entry and API-key clients. Class `public`, owner dungxbuif,
status `active`. The repo is read-only for this doc.

## Source

| Field | Value |
|---|---|
| Local checkout | `/home/dungxbuif/workspace/projects/mac-ocr/` (branch `codex/workspace-sync-20261023`, HEAD `4f02f42`) |
| GitLab | `dungxbuif/mac-ocr` (remote name `gitlab`; default branch unverified) |
| Repo docs | `README.md`, `docs/` (api, architecture, configuration, deployment/production.md, guides/mac-workers.md, `RELEASE_NOTES.md`) |
| Deployed revision | proxy image `homelab/macocr-proxy:scan-api-20261008` (`sha256:e6907a82…`), between `8d1f951` and `4810527`; native app 2.0.0 build 7 |

## Internal architecture

- `proxy/`: Go service `cmd/proxy` (HTTP `:8080`, scheduler, retention jobs) and `cmd/admin`; `proxy/admin-ui` (React) and `docs-site` are embedded at build time. Root `Dockerfile` is multi-stage.
- `native/`: Swift app, universal (arm64 + x86_64), macOS 13+, ad-hoc signed. Production build defaults: `MACOCR_DEFAULT_PROXY_URL=https://ocr.dungxbuif.com`, shared auth mode. Artifacts in `native/dist/`.
- Transport `NATIVE_TRANSPORT=websocket`: sockets are owned by one proxy process, so the proxy must stay at **1 replica**. Legacy HTTP transport is kept only for rollback.
- `omniscan/` (Mezon bot) is retired in the lab; its DB `omniscan` is marked retired.
- PostgreSQL holds accounts, API keys, documents and queue rows; Redis holds rate limits and TTL-bound results; S3 holds inputs and scan outputs.

## Runtime

| Field | Value |
|---|---|
| Host / placement | VM100 (`node.hostname==vm100-prod`) for the proxy; Mac mini `10.10.0.6` for the worker app (`/Applications/Mac OCR Native.app`, no local listener) |
| Stack / services | No stack. Standalone Swarm service `macocr-proxy` 1/1 (created 2026-09-15, spec updated 2026-10-21) |
| Image | `homelab/macocr-proxy:scan-api-20261008` — **local-only image on VM100**, no registry |
| Domain / exposure | `ocr.dungxbuif.com` · public → Pi5 Traefik router `ocr` → `tasks.macocr-proxy:8080`. Mac workers use the same host over WSS/443 |
| Networks | `edge-http-net`, `macocr-redis-net`, `pg-net` |
| Limits | 1 CPU / 1 GiB, no reservation |
| Update config | `stop-first`, `failure_action: rollback` |
| Healthcheck | `wget http://localhost:8080/healthz` every 30s (readiness is `/readyz`, not probed) |

## Data

| Store | Name | Backup class | Last restore evidence | RPO / RTO |
|---|---|---|---|---|
| PostgreSQL (`pgbouncer:6432`) | `macocr` | in `backup/inventory.yaml`; not in the Databasus restore-verified set | none recorded | not stated |
| Redis `redis-prod` | DB index 0 | none | n/a | results are TTL-bound by design |
| RustFS | bucket `mac-ocr` (also holds Family Tree objects under prefix `family-tree`) | in inventory; no scheduled RustFS backup | none | not stated |

## Secrets

Plain service env vars, not Swarm secrets. Sensitive names: `DATABASE_URL`,
`REDIS_URL`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`, `NATIVE_AUTH_SECRET`
(shared Bearer key also baked into the native app build),
`NOTIFICATION_ENCRYPTION_KEY`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`. Non-secret:
`WORKER_AUTH_MODE`, `NATIVE_TRANSPORT`, `PUBLIC_API_BASE_URL`,
`PUBLIC_DOCS_BASE_URL`, `MAX_UPLOAD_BYTES`, `APP_ENV`, `HTTP_ADDR`. 1Password
paths: (unverified). Rotating `NATIVE_AUTH_SECRET` requires rebuilding or
reconfiguring every Mac app.

## Delivery

- CI: none (no `.gitlab-ci.yml`). The image is built by hand on VM100 and tagged by date.
- Staging: none. Prod: manual `docker service update` from Pi5. Semaphore `app-deploy` spec lists `macocr-proxy`, but catalog marks it `deployable: false`.
- Native app: built on the Mac (`swift build -c release`), shared manually as DMG/ZIP.
- Rollback: Swarm auto-rollback; catalog rollback image is the same tag, so there is **no older image recorded**. Keep the prior proxy and native binaries before any change.

## Operations

- Health: `https://ocr.dungxbuif.com/healthz` (200, 2026-10-31); readiness `/readyz`; Swagger `/api/v1/docs`; admin `/admin/`.
- Logs: `docker service logs macocr-proxy` (Pi5); native app has its own log view.
- No OCR results / jobs stuck queued → check the Mac app is running and connected (Workers page in admin); check node is not paused/drained (state persists across restarts).
- Never scale the proxy above 1 replica while using WebSocket transport.

## Gate status

| Gate | State | Evidence / exception (expiry) |
|---|---|---|
| G0 Intake | partial | GitLab repo, catalog entry; no `app.yml` |
| G1 Build | fail | No CI; local-only image, no registry, no scan |
| G2 Security | fail | Credentials in plain env vars; one shared worker key |
| G3 Runtime | fail | Hand-created service, no stack, no reservations |
| G4 Data | fail | No recorded restore of `macocr` or bucket `mac-ocr` |
| G5 Observability | not assessed | |
| G6 Release | partial | Release notes v2.0.0; no staging, no rehearsed rollback |
| G7 Docs | partial | Good repo docs; `docs/deployment/production.md` names the lab domain (public-safe rule) |
| G8 Operate | not assessed | |

## Recent changes

- 2026-10-23: repo docs scrubbed of credential values (`4f02f42`, not a runtime change).
- 2026-10-08: proxy image `scan-api-20261008` (PDF text extraction, worker controls).
- 2026-10-06: v2.0.0 outbound WSS Mac workers, native app build 7.
