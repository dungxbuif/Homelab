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
repo: homelab-apps/mac-ocr
deployed_revision: "image scan-api-20261008 (runtime unchanged; CI/CD migration prepared on 2026-11-01)"
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
| Local checkout | `/Users/dungxbuif/workspace/projects/mac-ocr/` (branch `codex/macocr-ci-cd`, HEAD `9530dd2`) |
| GitLab | `homelab-apps/mac-ocr` (remote name `gitlab`; default branch unverified) |
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
| Image | Current runtime remains `homelab/macocr-proxy:scan-api-20261008`; the new release path targets `registry-gitlab.dungxbuif.com/homelab-apps/mac-ocr/proxy@sha256:…` |
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

## Delivery scope

This repository contains two delivery components. The lab CI/CD scope covers
only `proxy/`, the embedded admin/docs assets and the root `Dockerfile`, which
run as `macocr-proxy` on VM100. The `native/` Swift application runs on the
owner's Mac and is an `external-client`; it is deliberately excluded from the
lab CI/CD deploy pipeline. It keeps the repository Git flow and documentation
requirements and is released through the local Mac build/install procedure.

The proxy pipeline must not be triggered by a native-only change. A proxy
release must record the API/transport compatibility contract used by existing
native workers, but it does not build, sign, package or deploy the native app.

## Delivery

- Lab CI/CD target: `macocr-proxy` only. The repo now contains `.gitlab-ci.yml` and `docs/deployment/ci-cd.md` on the `codex/macocr-ci-cd` branch: validate/test → authenticated registry push/pull smoke → build once → run `macocr-admin migrate` from the immutable image on Pi5 via `pg-net` → deploy the immutable digest → `/healthz` and `/readyz` smoke. Production is triggered only by a protected `prod-<semver>` tag and remains one Swarm replica; migration failure blocks deploy.
- Runner placement: current evidence uses VM100 rootless runner #1 with tag `homelab-rootless`, locked to the active lab app scope. Pipeline #659 is green: jobs #2139 (Go), #2140 (admin UI), and #2141 (docs) passed. The VM110 `homelab-apps` runner IaC branch remains a future isolated option and is not used by this rollout.
- GitLab CI/CD common variables should use the private `homelab-apps` group scope. Instance-global variables are unavailable to the current GitLab account because it has no instance-admin scope; do not claim instance-global secret setup until the admin-scoped control plane is available.
- A private GitLab group `homelab-apps` (group ID `43`) was created on 2026-11-01 and `mac-ocr` was transferred into it. The local `gitlab` remote now points to `homelab-apps/mac-ocr`; the project remains private.
- Staging: none. Prod: the pipeline will perform the existing `docker service update` from the Pi5 Swarm manager after the global registry and deploy variables are provisioned. Semaphore `app-deploy` remains outside this pilot.
- Native app: external-client; built on the Mac (`swift build -c release`), shared manually as DMG/ZIP. It is not a lab CI/CD deployment target.
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
| G1 Build | partial | `.gitlab-ci.yml` is implemented and pipeline #659 is green on VM100; protected registry/deploy secrets, registry smoke, and tag deployment remain pending. The project belongs to the shared `homelab-apps` group |
| G2 Security | fail | Credentials in plain env vars; one shared worker key |
| G3 Runtime | fail | Hand-created service, no stack, no reservations |
| G4 Data | fail | No recorded restore of `macocr` or bucket `mac-ocr` |
| G5 Observability | not assessed | |
| G6 Release | partial | Proxy is the lab release target and now has a tag/digest pipeline definition; no GitLab execution, production registry image, or rollback rehearsal has been recorded yet |
| G7 Docs | partial | Good repo docs; `docs/deployment/production.md` names the lab domain (public-safe rule) |
| G8 Operate | not assessed | |

## Recent changes

- 2026-10-23: repo docs scrubbed of credential values (`4f02f42`, not a runtime change).
- 2026-10-08: proxy image `scan-api-20261008` (PDF text extraction, worker controls).
- 2026-10-06: v2.0.0 outbound WSS Mac workers, native app build 7.
- 2026-11-01: production migration gate and advisory-locked `macocr-admin migrate` command added to the GitLab release flow (`9530dd2`).
- 2026-11-01: private GitLab group `homelab-apps` created and `mac-ocr` transferred into it for the shared CI runner standard.
