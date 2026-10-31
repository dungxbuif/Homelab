---
type: Project
title: Whiteboard (devtool)
description: Self-hosted Excalidraw-style collaborative whiteboard (Go backend, React frontend, collab, MCP); Compose on VM100
generated:
  by: claude-code/opus-5.5
  at: "2026-10-31T16:00:00+07:00"
stale_after: "2027-01-29T16:00:00+07:00"
lifecycle: active
project: devtool
class: internal
owner: dungxbuif
repo: github.com/dungxbuif/whiteboard
deployed_revision: 325f9fd + uncommitted changes (images built 2026-10-21)
---

# Whiteboard

## Summary

Whiteboard is a rewrite of the Excalidraw ecosystem: a self-hosted
collaborative whiteboard with a Go clean-architecture backend, React/Vite
frontend, realtime collaboration server, a feature worker and an MCP adapter
for agents, plus AI features through an OpenAI-compatible provider. It runs at
`whiteboard.dungxbuif.com` as Compose project `whiteboard` on VM100. Class
`internal` (per gates doc example), owner dungxbuif, status `active`.

## Source

| Field | Value |
|---|---|
| Local checkout | `/home/dungxbuif/workspace/projects/devtool/` (origin `github.com/dungxbuif/whiteboard`, HEAD `0d6f7e0`, contains the deployed `325f9fd`). VM100 also keeps a git checkout in the deploy directory `/opt/apps/whiteboard/` with uncommitted changes |
| Git remote | `origin` = `github.com/dungxbuif/whiteboard.git` (`master`); GitLab mirror `dungxbuif/devtool` |
| Repo docs | `/opt/apps/whiteboard/README.md` (generic "repository-harness" text, not product-specific), `AGENTS.md`, `docs/` (`CONTEXT.md`, `architecture/`, `operations/DEPLOYMENT.md`, `operations/RELEASE_CHECKLIST.md`, `releases/CHANGELOG.md`, …) |
| Deployed revision | HEAD `325f9fd` (2026-10-21, "declare postgres network at compose root") with a dirty tree: `docker-compose.prod.yml`, `src/backend/cmd/server/main.go` and several docs modified |

Not related: `projects/devtool/references/ws-whiteboard` inside the checkout (2024 Excalidraw room
server) and `projects/selfhost/kubernetes-v1/whiteboard` (retired K8s manifests).

## Internal architecture

| Container | Role |
|---|---|
| `db-migrate` (`migrate/migrate:v4.17.1`) | One-shot forward migrations from `src/backend/migrations` |
| `whiteboard-backend` | Go HTTP API `:8080`, Casbin authz, SSO, authority listener on internal net |
| `whiteboard-feature-worker` | Background feature jobs (`/app/feature-worker`) |
| `whiteboard-collab` | Node realtime collaboration `:8082-8083`; `COLLAB_V2_ENABLED` flag |
| `whiteboard-mcp` | MCP adapter `:3002`, audit log on volume `whiteboard_mcp-audit`; `/mcp` returns 401 without credentials |
| `whiteboard-frontend` | Static React app `:80`, the only container routed from the edge |

An `authority` internal bridge (`172.29.240.0/28`, fixed IPs) carries
backend ↔ collab authority traffic. AI uses FPT `DeepSeek-V4.1-Flash` per
[VM100](../VM100.md). TURN credentials are configured for voice/video.

## Runtime

| Field | Value |
|---|---|
| Host / placement | VM100 |
| Stack / services | Compose project `whiteboard`, file `/opt/apps/whiteboard/docker-compose.prod.yml` (not Swarm) |
| Image | Built locally from source (`build:`), tags `whiteboard-{backend,feature-worker,collab,mcp,frontend}`; no registry, no digest |
| Domain / exposure | `whiteboard.dungxbuif.com` → Pi5 route `whiteboard` → `http://whiteboard-frontend:80` (no `lan-only` middleware). Public reachability through VPS HostSNI (unverified) |
| Networks | `edge-http-net` (backend, frontend), `pg-net`, `s3-net`, `whiteboard-app`, `authority` (internal) |
| Limits | backend 1 CPU / 1 GiB; feature-worker 0.5 / 256 MiB; collab 1 / 1 GiB; mcp 1 / 2 GiB; frontend 0.5 / 256 MiB |
| Hardening | worker, collab, mcp, frontend: read-only rootfs, `cap_drop: ALL`, `no-new-privileges`, pids limits. Backend has none of these |
| Healthchecks | all five healthchecked and `healthy` (2026-10-31) |
| Host ports | none |

## Data

| Store | Name | Backup class | Last restore evidence | RPO / RTO |
|---|---|---|---|---|
| PostgreSQL (Pi5 via `pg-net`) | `whiteboard` | Databasus job exists | none: not in the 2026-10-31 verified set ([audit](../deployments/databasus-audit-2026-10-31.md)) | not stated |
| Object storage (Pi5 RustFS via `s3-net`) | bucket from `S3_BUCKET` (name unverified) | none (no RustFS schedule) | none | not stated |
| MCP audit log | volume `whiteboard_mcp-audit` | none | none | n/a |
| Cutover snapshots | `/opt/apps/whiteboard/backups/<cutover>-<ts>/` (latest `dashboard-management-20261021T001701Z`) | manual | none | n/a |

## Secrets

| Secret | 1Password item | Used for |
|---|---|---|
| `/opt/apps/whiteboard/.env.prod` (mode 0600; symlink `whiteboard.env`): `DATABASE_URL`, `JWT_SECRET`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `TURN_PASSWORD`, `TURN_AUTH_SECRET`, `AI_API_KEY`, `COLLAB_JWT_SECRET`, `AUTHORITY_SERVICE_SECRET`, `MUTATION_GRANT_SECRET`, `COLLAB_INTERNAL_SECRET`, `SSO_ENCRYPTION_KEY` | (unverified) | app runtime |

Some secret-named variables are also interpolated in `docker-compose.prod.yml`
`environment:` blocks; confirm they reference `.env.prod` and are not literals
before committing that file. Repo docs: `docs/operations/auth-secrets-rotation.md`.

## Delivery

- CI: none found (no pipeline file observed; GitHub-only remote).
- Deploy: manual on VM100 in `/opt/apps/whiteboard`: pull/edit, back up into
  `backups/`, `docker compose -f docker-compose.prod.yml config --quiet`, `up -d --build`.
  Repo procedure: `docs/operations/DEPLOYMENT.md`, `RELEASE_CHECKLIST.md`.
- Staging: none.
- Rollback: `git checkout` the previous commit and rebuild; compose backups
  `docker-compose.prod.yml.bak-*` and env backup
  `.env.prod.bak-nohomelab-20261020134411` exist. Previous images are not retained by tag.

## Operations

- Health: `https://whiteboard.dungxbuif.com/healthz` (frontend; unverified externally); backend `/healthz` inside container.
- Logs: `docker logs whiteboard-backend` (and other containers) on VM100.
- Known issues: the VM100 deploy dir has uncommitted changes that are not in the workstation checkout (reconcile before the next release); README is a template harness text, not product docs.

## Gate status

| Gate | State | Evidence / exception (expiry) |
|---|---|---|
| G0 Intake | fail | No GitLab repo, no `app.yml` |
| G1 Build | fail | No CI; images built on host; no registry |
| G2 Security | partial | No host ports, most containers hardened; secrets in env file; backend unhardened |
| G3 Runtime | fail | Manual Compose, not a Swarm stack |
| G4 Data | partial | Databasus job for `whiteboard` DB; no restore record; object storage unbacked |
| G5 Observability | not assessed | |
| G6 Release | partial | Release notes in `docs/releases/`; no staging, no rehearsed rollback |
| G7 Docs | partial | docs/ rich; README not product-specific (describes repository-harness) |
| G8 Operate | not assessed | |

## Recent changes

- 2026-10-21: enterprise parity release on VM100 (`docs/releases/2026-10-21-enterprise-parity-vm100.md`, HEAD `325f9fd`)
- 2026-10-21: resource limits added to `docker-compose.prod.yml`
- 2026-10-20: AI provider cutover (snapshot `backups/ai-provider-cutover-20261020T152848Z`)
- 2026-10-19: collaboration v2 cutover (`docs/releases/2026-10-19-collaboration-v2.md`)
- 2026-10-15: first VM100 release
