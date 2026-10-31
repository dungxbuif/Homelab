---
type: Project
title: RelayHub
description: Managed event, webhook, queue and realtime relay; Rust v1 Swarm stack on VM100 with the legacy Go Compose kept as rollback
generated:
  by: claude-code/opus-5.5
  at: "2026-10-31T16:00:00+07:00"
stale_after: "2027-01-29T16:00:00+07:00"
lifecycle: active
project: relayhub
class: public
owner: dungxbuif
repo: dungxbuif/relayhub
deployed_revision: c61e998 (API image), admin v1-public-20261031 (source revision unverified)
---

# RelayHub

## Summary

RelayHub lets applications exchange events, signed webhooks, queue jobs,
realtime channel messages and short remote functions through one managed
service. The Rust v1 rewrite (`relayhub-v1` Swarm stack) is the public writer
at `relayhub.dungxbuif.com`. The legacy Go implementation still runs on VM100
as Compose project `prod`, not routed, kept only as a rollback target.
Class `public`, owner dungxbuif, status `active`.

Related internal references (keep them, do not merge into public docs):

- [RelayHub internals](../services/relayhub-internals.md): source map, runtime design, operational controls
- [RelayHub product docs release evidence](../services/relayhub-product-docs.md): public docs boundary and release procedure

## Source

| Field | Value |
|---|---|
| Local checkout | `/home/dungxbuif/workspace/projects/RelayHub/` (checked out on `codex/centrifugo-upstream-baseline`, HEAD `9c6baa0`, 2026-10-31) |
| GitLab | `dungxbuif/relayhub` (default branch `main`); GitHub mirror `dungxbuif/RelayHub` |
| Repo docs | `README.md`, `CHANGELOG.md`, `docs/` (architecture, decisions, developer, operations, user), public site `web/docs/` |
| Deployed revision | v1 API `c61e998` ("expose live agent presence to dashboard", contained in `main`); stack file from `f933e49` (2026-10-31). Legacy Go `eee9e7c` |

## Internal architecture

- `relayhub` (Rust `relayhub-server`, `rust/src/*`): API, ingest, delivery,
  agent WebSocket gateway, webhooks and realtime in one process. Serves
  `/api/v1/*` and `/hooks/*`.
- `admin`: operator/dashboard UI (`web/remake-admin/`), served on the same
  hostname for every path that is not API or hooks.
- `nats` (JetStream, volume `relayhub-v1_relayhub-v1-nats`): durable work signals.
- `redis` (no persistence, 128 MB `noeviction`): presence and bounded realtime state.
- PostgreSQL on Pi5 via `pgbouncer:6432` is authoritative (identity, events,
  outbox, delivery, audit). Details in [internals](../services/relayhub-internals.md).
- Public docs intentionally hide component names and topology; see the
  [product docs boundary](../services/relayhub-product-docs.md).

## Runtime

| Field | Value |
|---|---|
| Host / placement | VM100 (`node.hostname == vm100-prod`) for all four services |
| Stack / services | Swarm stack `relayhub-v1` deployed from `RelayHub/deploy/production/stack-staging.yaml` (not in `homelab-ops`) → `relayhub-v1_relayhub`, `_admin`, `_nats`, `_redis` |
| Image | `relayhub-v1:c61e998`, `relayhub-admin:v1-public-20261031` (local VM100 images, no registry, no digest); `nats:2.14.5-alpine@sha256:d4ac3588…`, `redis:7.4-alpine@sha256:8da19c73…` |
| Domain / exposure | `relayhub.dungxbuif.com`: Pi5 file-provider routes `relayhub` (`/api/v1`, `/hooks/`) → `tasks.relayhub-v1_relayhub:8080`, `relayhub-ui` → `tasks.relayhub-v1_admin:8080`. Public via VPS HostSNI (unverified) |
| Host port | `relayhub` publishes `18080 → 8080` in host mode on VM100 (violates the no-host-ports rule) |
| Networks | `relayhub`: `edge-http-net`, `pg-net`, `relayhub-v1_relayhub-v1`; `admin`: `edge-http-net`; NATS/Redis: `relayhub-v1_relayhub-v1` only |
| Limits | `relayhub` 1 CPU / 768 MiB; `admin` 0.25 CPU / 128 MiB; NATS and Redis none; no reservations |
| Healthcheck | `relayhub` curls `/api/v1/openapi.json`; admin, NATS, Redis none |
| Update config | `failure_action: pause` on all services |

Legacy rollback runtime (VM100 Compose `prod`, `/opt/apps/relayhub/prod/`,
files `compose.yml` + `compose.override.yml` + `compose.release.yml`):
`relayhub-api` and `relayhub-worker` on `homelab/relayhub:prod-eee9e7c`,
`relayhub-nats`, `relayhub-redis`; 1 CPU / 1 GiB each; all healthchecked;
networks `relayhub-net`, `pg-net` (api also `edge-http-net`). No Pi5 route
points at it. A 0/0 Swarm service `relayhub` (`bootstrap-20260914`) is a
leftover cleanup candidate.

## Data

| Store | Name | Backup class | Last restore evidence | RPO / RTO |
|---|---|---|---|---|
| PostgreSQL (Pi5, via PgBouncer) | `relayhub_v1_staging_20261030` (active v1 DB, despite the name) | none: no Databasus job documented | none | not stated |
| PostgreSQL (Pi5) | `relayhub` (legacy, rollback) | Databasus → Google Drive | 2026-10-31: backup + `pg_restore` verify, 30 tables ([upgrade ledger](../deployments/version-upgrade-2026-10-31.md)) | not stated |
| NATS volume | `relayhub-v1_relayhub-v1-nats` | none | none | rebuildable from PostgreSQL outbox (unverified) |
| Redis | in-memory only | none (by design) | n/a | n/a |

## Secrets

| Secret | 1Password item | Used for |
|---|---|---|
| `relayhub_v1_staging_db` (Swarm, unversioned name) | (unverified) | PgBouncer password for role `relayhub_v1_staging_app` |
| Legacy `prod`: env file `/opt/apps/relayhub/prod/relayhub.env` (names: `RELAYHUB_SIGNING_SECRET`, `RELAYHUB_POSTGRES_URL`, `RELAYHUB_SECRET_ENCRYPTION_KEY`, `RELAYHUB_NATS_USERNAME`/`_PASSWORD`, `RELAYHUB_REDIS_PASSWORD`, …) | (unverified) | legacy Go runtime |

v1 non-secret env: `NATS_URL`, `REDIS_URL`, `RELAYHUB_NAMESPACE`, `HTTP_ADDR`.
NATS and Redis in the v1 stack run without credentials (private overlay only).

## Delivery

- CI: GitHub Actions in the repo (`.github/workflows/ci.yml`, `admin-ci.yml`,
  `publish-typescript-sdk.yml`); no `.gitlab-ci.yml`, no `platform/ci-templates`.
- Build: images built on VM100 and tagged by commit; not pushed to a registry.
- Deploy: manual `docker stack deploy -c deploy/production/stack-staging.yaml relayhub-v1`
  from the Pi5 manager (unverified exact command). No staging environment;
  `deploy/remake/compose.yaml` is a disposable release rehearsal only.
- Rollback within v1: redeploy the stack with the previous image tag (must still
  exist on VM100). Rollback to legacy: repoint the Pi5 `relayhub` routes to the
  `prod` Compose API, which still uses the `relayhub` DB; v1 data written since
  cutover is not carried back.

## Operations

- Health: `https://relayhub.dungxbuif.com/api/v1/openapi.json`; legacy `readyz` on `:8080`/`:9090` inside containers.
- Logs: `docker service logs relayhub-v1_relayhub` (Pi5); legacy `docker logs relayhub-api` (VM100).
- Runbooks in repo: `docs/operations/runbook.md`, `remake-cutover.md`, `release-note-v1-prod.md`.
- Known issues: route 502 → check `tasks.relayhub-v1_relayhub` DNS from `edge-traefik-pi5`; v1 DB has no backup (BACKLOG R4).

## Gate status

| Gate | State | Evidence / exception (expiry) |
|---|---|---|
| G0 Intake | fail | No `homelab-ops/stacks/relayhub/app.yml` |
| G1 Build | fail | Local-only images, no registry digest, no Trivy/SBOM/cosign |
| G2 Security | fail | Host port `18080`; secret name not versioned; legacy secrets in env file |
| G3 Runtime | fail | Stack lives in app repo, deployed by hand; `failure_action: pause`; no limits/healthchecks on admin/NATS/Redis |
| G4 Data | fail | Active DB `relayhub_v1_staging_20261030` not enrolled, no restore record (legacy `relayhub` verified 2026-10-31) |
| G5 Observability | not assessed | No blackbox probe documented |
| G6 Release | partial | CHANGELOG `1.0.0` (2026-09-20) for Go; v1 has no semver tag or staging smoke |
| G7 Docs | partial | Repo README/docs exist; vault doc now exists; revision recorded |
| G8 Operate | not assessed | Legacy `prod` + 0/0 `relayhub` service pending retirement (BACKLOG P1/P5) |

## Recent changes

- 2026-10-31: product docs D1–D4 + review fixes on branch `codex/relayhub-product-docs` (not merged)
- 2026-10-31: Rust v1 edge and dashboard promoted to `relayhub.dungxbuif.com` (`f933e49`, API `c61e998`)
- 2026-10-31: legacy Compose Redis pinned to `7.4` digest `8da19c73…`
