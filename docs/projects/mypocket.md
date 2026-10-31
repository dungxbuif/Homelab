---
type: Project
title: MyPocket
description: Personal finance Go API + worker for the native iOS app, API-only at money.dungxbuif.com on VM100
generated:
  by: claude-code/opus-5.5
  at: "2026-10-31T18:00:00+07:00"
stale_after: "2027-01-29T18:00:00+07:00"
lifecycle: active
project: MyPocket
class: public
owner: dungxbuif
repo: dungxbuif/mypocket
deployed_revision: v1.2.1 (837bd505)
---

# MyPocket

## Summary

Owner-operated personal finance backend (wallets, transactions, budgets,
recurring items, portfolio, AI advisor, OCR receipt entry, MCP endpoint). The
native iOS app (`mobile-ios/`) talks to `https://money.dungxbuif.com/api/v1`.
Since 2026-10-13 production is **API-only**: the web UI service is kept at
0/0 for rollback. Class `public` (real financial data), owner dungxbuif,
status `active`.

## Source

| Field | Value |
|---|---|
| Local checkout | `/home/dungxbuif/workspace/projects/MyPocket/` (on branch `codex/workspace-unreleased-20261028`, local HEAD `b4ea4103`) |
| GitLab | `dungxbuif/mypocket` (remote name `gitlab`; default branch `main`) |
| Repo docs | `docs/README.md`, `docs/architecture/` (API, ERD, WORKER, OCR_API), `docs/operations/DEPLOYMENT.md`, `docs/releases/CHANGELOG.md` |
| Deployed revision | tag `v1.2.1` = `837bd505` (image `release-1.2.1-837bd505`, rolled out 2026-10-20) |

## Internal architecture

- `backend/` Go module: `cmd/api` (`/app/api`, Gin, HTTP `:8080`), `cmd/worker` (`/app/worker`, one pass every 60s: recurring transactions, budget periods, advisor idle expiry, budget notifications), `/app/migrate` (golang-migrate, forward-only; DB at migration 41).
- `app/`: Vite web UI (image `mypocket-web`), retired from the route.
- External calls: AI provider (OpenAI-compatible `AI_BASE_URL`), OCR via the lab OCR platform (`OCR_BASE_URL`, see [mac-ocr](./mac-ocr.md)), Google OAuth, APNs/Web Push, RustFS S3 for attachments.
- SQL logging is redacted to statement class only (ADR-019). Do not enable raw SQL logging.

## Runtime

| Field | Value |
|---|---|
| Host / placement | VM100 (`node.hostname==vm100-prod`), `linux/amd64` |
| Stack / services | No stack. Standalone services `mypocket-api` 1/1, `mypocket-worker` 1/1, `mypocket-web` 0/0 (created 2026-09-12) |
| Image | `registry.dungxbuif.com/mypocket-api:release-1.2.1-837bd505@sha256:34226ef0700f1ea4ff05d2c3de4d0fc0488d28ef71f7b4c735b09172c3d1fd54` (api + worker). Web: `mypocket-web:release-d5c6ba8c@sha256:86446191…` |
| Domain / exposure | `money.dungxbuif.com` · public → Pi5 Traefik router `money` → `tasks.mypocket-api:8080`. `/` serves nothing by design |
| Networks | api: `data-net`, `mypocket-net`, `mypocket-redis-net`, `edge-http-net`. worker: same minus `edge-http-net`. (catalog still lists `homelab-net`; live spec does not) |
| Limits | api 1 CPU / 1 GiB; worker 0.5 CPU / 512 MiB; web none. No reservations |
| Update config | api/worker `stop-first`, `failure_action: rollback`; web `pause` |
| Healthcheck | api `wget http://127.0.0.1:8080/api/v1/health`; worker **none**; web `wget /` |

## Data

| Store | Name | Backup class | Last restore evidence | RPO / RTO |
|---|---|---|---|---|
| PostgreSQL (Pi5 via `pgbouncer:6432`) | `mypocket` | listed in `homelab-ops/backup/inventory.yaml`; not in the Databasus restore-verified set | none recorded. Ad-hoc pre-release `pg_dump -Fc` on VM100 `/tmp/mypocket-pre-1.2.1.dump` (2026-10-20) | not stated |
| Redis `redis-prod` | DB index 1 | none (no Redis backup) | n/a | cache/queue, rebuildable (unverified) |
| RustFS | bucket `mypocket` | in inventory; no scheduled RustFS backup | none | not stated |

`/tmp` on VM100 is not a backup location; those dumps can vanish on reboot.

## Secrets

All configuration, including credentials, is injected as **plain service env
vars**, not Swarm secrets. Sensitive names: `DATABASE_URL`, `REDIS_URL`,
`JWT_SECRET`, `COOKIE_SECRET`, `CSRF_SECRET`, `API_KEY_HASH_SECRET`,
`AUDIT_HASH_SECRET`, `AI_API_KEY`, `OCR_API_KEY`, `GOOGLE_CLIENT_SECRET`,
`S3_ACCESS_KEY(_ID)`, `S3_SECRET_KEY`/`S3_SECRET_ACCESS_KEY`,
`VAPID_PRIVATE_KEY`, `FEEDBACK_AGENT_TOKEN`, `SEED_USER_PASSWORD` (api only).
1Password item paths: (unverified).

## Delivery

- CI: none (no `.gitlab-ci.yml`). Images are built locally (amd64 cross-build) and pushed to the Pi5 `registry.dungxbuif.com`.
- Staging: none. Prod: manual `docker service update --image <digest>` from the Pi5 manager, after a `pg_dump` and `/app/migrate up` from the release image, per `docs/operations/DEPLOYMENT.md`.
- Rollback: update both services to the previous digest (prior: `release-20261020-a2de756` `sha256:5b54465e…`). Schema incidents: restore the dump to a disposable DB first, then an owner-approved window. Never force a migration.
- Model updates: `homelab-ops/automation/maintenance/update-mypocket-model.sh`.

## Operations

- Health: `https://money.dungxbuif.com/api/v1/health` (200, 2026-10-31); Swagger `/api/v1/docs/index.html`.
- Logs: `docker service logs mypocket-api` / `mypocket-worker` (from Pi5).
- Worker failing on a missing column after an image update → migrations were not run; run `/app/migrate up` from the API image (2026-10-16 incident).
- Do not scale `mypocket-web` up without owner approval; it also needs the Traefik route restored.

## Gate status

| Gate | State | Evidence / exception (expiry) |
|---|---|---|
| G0 Intake | partial | GitLab repo, catalog entry `mypocket`; no `app.yml` |
| G1 Build | fail | No CI; image in Pi5 registry, not GitLab Registry; no scan/SBOM/signature |
| G2 Security | fail | Credentials in plain env vars, not Swarm secrets |
| G3 Runtime | fail | Hand-created services, no stack; worker has no healthcheck; no reservations |
| G4 Data | fail | No recorded restore of `mypocket`; RPO/RTO not stated |
| G5 Observability | not assessed | |
| G6 Release | partial | Semver tags `v1.2.x` and release notes; no staging, rollback not rehearsed |
| G7 Docs | partial | Rich `docs/`; root `README.md` describes "Harness", not MyPocket |
| G8 Operate | not assessed | Catalog `observed_image` values are stale (`auth-12572c87`) |

## Recent changes

- 2026-10-20: v1.2.1 (`837bd505`) to api + worker, migration 40 → 41.
- 2026-10-20: `release-20261020-a2de756`, migration 37 → 40 (backup skipped by owner approval).
- 2026-10-19: `release-20261019-uat2`, migrations 35–37.
- 2026-10-13: API-only mode; `mypocket-web` scaled to 0/0.
