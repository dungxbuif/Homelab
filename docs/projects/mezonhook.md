---
type: Project
title: MezonHook
description: Static Vite/React Mezon webhook message builder, public demo at mezonhook.dungxbuif.com on VM100 Swarm
generated:
  by: claude-code/opus-5.5
  at: "2026-10-31T18:00:00+07:00"
stale_after: "2027-01-29T18:00:00+07:00"
lifecycle: active
project: mezonhook
class: public
owner: dungxbuif
repo: dungxbuif/mezonhook
deployed_revision: "image vm100-20260911 (built 2026-09-11 00:09 +07; likely 3dc7541, unverified)"
---

# MezonHook

## Summary

Browser-only, Discohook-style editor for composing and previewing ordered
Mezon Channel Webhook messages (templates, embeds, fields, actions; up to 20
messages and 10 targets). Projects are stored in browser storage; webhook URLs
stay in session memory only. The browser posts directly to
`webhook.mezon.ai`; the lab serves static files only. Class `public` (public
demo), owner dungxbuif, status `active`.

## Source

| Field | Value |
|---|---|
| Local checkout | `/home/dungxbuif/workspace/projects/mezonhook/` (branch `codex/mvp-webhook-builder`, HEAD `8615566`, 2026-10-23) |
| GitLab | `dungxbuif/mezonhook` (remote name `gitlab`; default branch unverified, `main` assumed) |
| Repo docs | `README.md`, `docs/USAGE.md`, `docs/DEPLOYMENT.md`, `CONTRIBUTING.md`, `SECURITY.md` |
| Deployed revision | `homelab/mezonhook:vm100-20260911` (`sha256:9f2bcbce…`). Last commit before the build is `3dc7541` (2026-09-08); built from a working tree, exact sha unverified. The 2026-10-23 "webhook payload workbench" (`f652097`) is **not deployed** |

## Internal architecture

- npm workspaces: `apps/web` (Vite + React), `packages/schema` (draft validation, Mezon payload conversion).
- `Dockerfile`: `node:20-alpine` build stage, runtime `nginxinc/nginx-unprivileged:alpine` (non-root), listens `:8080`, SPA fallback.
- `nginx.conf` sets CSP (`connect-src 'self' https://webhook.mezon.ai`), `X-Frame-Options DENY`, `no-referrer`, `nosniff`.
- No backend, no data, no secrets. Delivery depends on Mezon CORS allowing the origin.

## Runtime

| Field | Value |
|---|---|
| Host / placement | VM100 (`node.hostname==vm100-prod`), amd64 |
| Stack / services | No stack. Standalone Swarm service `mezonhook` 1/1 (created 2026-09-15, spec updated 2026-10-21) |
| Image | `homelab/mezonhook:vm100-20260911` — **local-only image on VM100**, no registry |
| Domain / exposure | `mezonhook.dungxbuif.com` · public → Pi5 Traefik router `mezonhook` → `tasks.mezonhook:8080` |
| Networks | `edge-http-net` |
| Limits | 0.5 CPU / 512 MiB, no reservation |
| Update config | `start-first`, `failure_action: rollback`, monitor 30s |
| Healthcheck | `wget -qO- --timeout=3 http://127.0.0.1:8080/` every 30s |

## Data

| Store | Name | Backup class | Last restore evidence | RPO / RTO |
|---|---|---|---|---|
| none | stateless; user projects live in each browser | n/a | n/a | rebuild image from git |

## Secrets

None. Users' Mezon webhook URLs never reach the server.

## Delivery

- CI: GitHub Actions `.github/workflows/ci.yml` (npm ci, test, build) — not GitLab CI, and it does not build or push an image.
- Staging: none. Prod: `docker build` on VM100 with a date tag, then `docker service update --image` from Pi5 (procedure inferred from the tag, unverified).
- Rollback: Swarm auto-rollback on failed update only. No previous image recorded.

## Operations

- Health: `https://mezonhook.dungxbuif.com/` (200, 2026-10-31).
- Logs: `docker service logs mezonhook` (Pi5).
- "Send" fails in the browser → usually Mezon CORS or the client's network, not the lab (see repo `docs/DEPLOYMENT.md`).
- Image is lost if VM100 Docker storage is wiped; rebuild from git.

## Gate status

| Gate | State | Evidence / exception (expiry) |
|---|---|---|
| G0 Intake | partial | GitLab repo, runtime policy entry; no `app.yml` |
| G1 Build | fail | No GitLab CI image build; local-only image; no scan/SBOM |
| G2 Security | partial | No secrets, no host ports, non-root runtime, CSP set; Renovate unverified |
| G3 Runtime | fail | Hand-created service, no stack, no reservations |
| G4 Data | pass | Stateless; nothing to restore |
| G5 Observability | not assessed | |
| G6 Release | fail | No tags or release notes |
| G7 Docs | partial | README + usage/deployment docs; no `docs/configuration.md`, CHANGELOG; deployment doc names the lab domain |
| G8 Operate | not assessed | |

## Recent changes

- 2026-10-21: service spec updated (edge/network migration window; detail unverified).
- 2026-09-15: Swarm service `mezonhook` created on VM100 with image `vm100-20260911`.
