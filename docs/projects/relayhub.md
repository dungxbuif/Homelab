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
deployed_revision: 731047e (public release tag; Rust runtime content c61e998); Go production runtime 731047e (not public)
canary_image: registry-gitlab.dungxbuif.com/dungxbuif/relayhub@sha256:4331063e39eb42caa722ae80aa656348d384e425c082cf451c50f46730261234
go_production_image: registry-gitlab.dungxbuif.com/dungxbuif/relayhub@sha256:4331063e39eb42caa722ae80aa656348d384e425c082cf451c50f46730261234
public_release_image: relayhub-v1:731047e (VM100 local Swarm image; previous tag c61e998 retained)
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
| Local checkout | `/home/dungxbuif/workspace/projects/RelayHub/` (operator worktree remains on `codex/centrifugo-upstream-baseline`, HEAD `9c6baa0`; release source is `main` `731047e`, 2026-10-31) |
| GitLab | `dungxbuif/relayhub` (default branch `main`); GitHub mirror `dungxbuif/RelayHub` |
| Repo docs | `README.md`, `CHANGELOG.md`, `docs/` (architecture, decisions, developer, operations, user), public site `web/docs/` |
| Deployed revision | Public Swarm release tag `731047e` (Rust binary content unchanged from `c61e998`; stack file from `f933e49`); Go production runtime `731047e`; rollback image alias preserves legacy Go `eee9e7c` |

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
| Image | `relayhub-v1:731047e` (previous `relayhub-v1:c61e998` retained; same image ID `sha256:a7281797…`), `relayhub-admin:v1-public-20261031` (local VM100 images, no registry, no digest); `nats:2.14.5-alpine@sha256:d4ac3588…`, `redis:7.4-alpine@sha256:8da19c73…` |
| Domain / exposure | `relayhub.dungxbuif.com`: Pi5 file-provider routes `relayhub` (`/api/v1`, `/hooks/`) → `tasks.relayhub-v1_relayhub:8080`, `relayhub-ui` → `tasks.relayhub-v1_admin:8080`. Public via VPS HostSNI (unverified) |
| Host port | `relayhub` publishes `18080 → 8080` in host mode on VM100 (violates the no-host-ports rule) |
| Networks | `relayhub`: `edge-http-net`, `pg-net`, `relayhub-v1_relayhub-v1`; `admin`: `edge-http-net`; NATS/Redis: `relayhub-v1_relayhub-v1` only |
| Limits | `relayhub` 1 CPU / 768 MiB; `admin` 0.25 CPU / 128 MiB; NATS and Redis none; no reservations |
| Healthcheck | `relayhub` curls `/api/v1/openapi.json`; admin, NATS, Redis none |
| Update config | `failure_action: pause` on all services |

Go release canary (isolated, not public): VM100 Compose project
`relayhub-canary` from `/opt/apps/relayhub/src/compose.yaml`, bound to
`18081 -> 8080`. It uses its own Postgres/NATS/Redis named volumes and a
generated private env file at `/opt/apps/relayhub/canary/relayhub.env`; it
must not be pointed at the live v1 or legacy database. Current image is pinned
by the shared GitLab Registry digest in the frontmatter. Public routing remains
on `relayhub-v1`; the canary is for release acceptance only.

Go production/rollback runtime (VM100 Compose `prod`, `/opt/apps/relayhub/prod/`,
files `compose.yml` + `compose.override.yml` + `compose.release.yml`):
`relayhub-api` and `relayhub-worker` on local alias `homelab/relayhub:prod-eee9e7c`,
currently backed by registry digest
`sha256:4331063e39eb42caa722ae80aa656348d384e425c082cf451c50f46730261234`
(`731047e`). The previous image is preserved as
`homelab/relayhub:rollback-eee9e7c-20261031`.
`relayhub-nats`, `relayhub-redis`; 1 CPU / 1 GiB each; all healthchecked;
networks `relayhub-net`, `pg-net` (api also `edge-http-net`). No Pi5 route
points at it; the public hostname remains on Rust v1. A 0/0 Swarm service
`relayhub` (`bootstrap-20260914`) is a leftover cleanup candidate.

## Production acceptance (2026-10-31)

- Production Go API/worker were recreated on VM100 from the immutable shared
  registry digest above; both are healthy, restart count 0, and the worker
  readiness check passes. This is a production-runtime validation, not a
  public DNS cutover: `relayhub.dungxbuif.com` remains Rust v1 for rollback.
- Before rollout, PostgreSQL was dumped to
  `/opt/apps/relayhub/backups/relayhub-prod-20261031T055828Z.dump`, mode 0600,
  93,618 bytes. `pg_restore --list` returned 208 entries. The old image remains
  available under the rollback alias above.
- A disposable TypeScript SDK client ran against the production API through a
  temporary localhost-only tunnel. It created an app and queue, published an
  event, replayed the same idempotency key and received the same event ID,
  pulled and acknowledged the delivery, and received a realtime WebSocket
  message. The app, queue, test user and temporary port were cleaned up; app
  history is retained but the synthetic apps are disabled because event
  foreign keys preserve audit history.
- Public smoke checks after cleanup: `/healthz`, `/readyz`,
  `/api/v1/openapi.json`, and `/admin/` all returned HTTP 200. No public route
  was changed during this acceptance run.

## Release integration and deployment (2026-10-31)

- `codex/relayhub-rust-v1` was already an ancestor of `main`; the release
  code was therefore integrated without a duplicate merge commit. The release
  worktree was clean after acceptance and is eligible for cleanup; the remote
  branch is retained for provenance.
- Fresh `bash scripts/remake-acceptance.sh` passed every gate: Rust format,
  locked check/unit/contracts/services/identity/durability/delivery/webhooks/
  realtime/connector/recovery/docs, Node typecheck/build/acceptance, Go race
  acceptance/vet, dashboard typecheck/build/browser acceptance, artifact
  build/contracts, disposable live-host migration/readiness, authenticated
  durable publish/status, and graceful drain.
- The public Swarm service `relayhub-v1_relayhub` was updated on the manager
  `rpivn` from `relayhub-v1:c61e998` to `relayhub-v1:731047e`, constrained to
  `vm100-prod`. Swarm reported `update completed`, one running task, and the
  task healthcheck is healthy. The image ID is unchanged because the Rust
  runtime had no source changes after `c61e998`; the new tag records the
  integrated `main` release state.
- Rollback is `docker service update --image relayhub-v1:c61e998
  relayhub-v1_relayhub` from the Pi manager. The Go rollback image remains
  `homelab/relayhub:rollback-eee9e7c-20261031`.

## Data

| Store | Name | Backup class | Last restore evidence | RPO / RTO |
|---|---|---|---|---|
| PostgreSQL (Pi5, via PgBouncer) | `relayhub_v1_staging_20261030` (active v1 DB, despite the name) | none: no Databasus job documented | none | not stated |
| PostgreSQL (Pi5) | `relayhub` (Go production/rollback) | Databasus → Google Drive | 2026-10-31: backup + `pg_restore` verify, 208 restore-list entries ([upgrade ledger](../deployments/version-upgrade-2026-10-31.md)) | not stated |
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
- Build: main release `731047e` is pushed to both GitHub and GitLab; the Go
  canary image is pushed to the shared GitLab Registry and deployed by digest.
  The Docker build runs the host release gates before packaging the image.
- Deploy: manual `docker stack deploy -c deploy/production/stack-staging.yaml relayhub-v1`
  from the Pi5 manager (unverified exact command). No staging environment;
  `deploy/remake/compose.yaml` is a disposable release rehearsal only.
- Canary deploy: on VM100, pull the immutable registry tag/digest, retag the
  local Compose alias `relayhub:local`, then run `docker compose -p
  relayhub-canary ... up -d --no-build --wait`. Verify `/healthz`,
  `/readyz`, `/metrics`, `/openapi.json`, `/llms.txt`, and `/admin/`
  before any promotion.
- Rollback within v1: redeploy the stack with the previous image tag (must still
  exist on VM100). Rollback to legacy: repoint the Pi5 `relayhub` routes to the
  `prod` Compose API, which still uses the `relayhub` DB; v1 data written since
  cutover is not carried back.

## Operations

- Health: `https://relayhub.dungxbuif.com/api/v1/openapi.json`; legacy `readyz` on `:8080`/`:9090` inside containers.
- Logs: `docker service logs relayhub-v1_relayhub` (Pi5); legacy `docker logs relayhub-api` (VM100).
- Canary: `docker compose -p relayhub-canary logs relayhub-api relayhub-worker`
  and `curl http://127.0.0.1:18081/readyz` on VM100. Keep the canary isolated
  until the public Rust stack has a separate approved rollout.
- Runbooks in repo: `docs/operations/runbook.md`, `remake-cutover.md`, `release-note-v1-prod.md`.
- Known issues: route 502 → check `tasks.relayhub-v1_relayhub` DNS from `edge-traefik-pi5`; v1 DB has no backup (BACKLOG R4).

## Gate status

| Gate | State | Evidence / exception (expiry) |
|---|---|---|
| G0 Intake | fail | No `homelab-ops/stacks/relayhub/app.yml` |
| G1 Build | partial | Go canary uses the shared GitLab Registry digest; Trivy/SBOM/cosign are still not attached |
| G2 Security | fail | Host port `18080`; secret name not versioned; legacy secrets in env file |
| G3 Runtime | fail | Stack lives in app repo, deployed by hand; `failure_action: pause`; no limits/healthchecks on admin/NATS/Redis |
| G4 Data | fail | Active DB `relayhub_v1_staging_20261030` not enrolled, no restore record (legacy `relayhub` verified 2026-10-31) |
| G5 Observability | not assessed | No blackbox probe documented |
| G6 Release | pass | Rust release acceptance passed all listed gates; public Swarm update to `relayhub-v1:731047e` completed with one healthy task and public smoke returned 200 |
| G7 Docs | partial | Repo README/docs exist; vault doc now exists; revision recorded |
| G8 Operate | not assessed | Legacy `prod` + 0/0 `relayhub` service pending retirement (BACKLOG P1/P5) |

## Recent changes

- 2026-10-31: product docs D1–D4 + review fixes on branch `codex/relayhub-product-docs` (not merged)
- 2026-10-31: Rust v1 edge and dashboard promoted to `relayhub.dungxbuif.com` (`f933e49`, API `c61e998`)
- 2026-10-31: legacy Compose Redis pinned to `7.4` digest `8da19c73…`
- 2026-10-31: Go Admin-parity canary deployed on VM100 from shared registry
  image `731047e`; Admin E2E passed 19/20 (one intentional mobile keyboard
  skip), Go and TypeScript clients passed live app/queue/realtime flows, and
  a post-restart readiness/session check passed. A real SDK bug where `202`
  with an empty body was parsed as JSON was fixed and included in the image.
- 2026-10-31: Go production runtime was upgraded on VM100 to `731047e` after
  a verified PostgreSQL backup. A disposable TypeScript production client
  passed event idempotency, queue pull/ack, and realtime WebSocket checks;
  public routing stayed on Rust v1 and the previous Go image was retained for
  rollback.
- 2026-10-31: Rust release worktree was verified, found already contained in
  `main`, and deployed as `relayhub-v1:731047e`; Swarm update completed and
  public health/docs/admin smoke checks returned HTTP 200.
