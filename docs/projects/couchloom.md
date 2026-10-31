---
type: Project
title: CouchLoom
description: Private MCP server and local semantic index over the Obsidian CouchDB vault; Compose on VM100
generated:
  by: claude-code/opus-5.5
  at: "2026-10-31T16:00:00+07:00"
stale_after: "2027-01-29T16:00:00+07:00"
lifecycle: active
project: couchloom
class: internal
owner: dungxbuif
repo: dungxbuif/couchloom
deployed_revision: 9541933
---

# CouchLoom

## Summary

CouchLoom turns the Obsidian Self-hosted LiveSync documents in Pi5 CouchDB into
an authenticated MCP surface for agents (read/list/search/create/edit, no
delete/move/rename) and keeps a local pgvector semantic index embedded by a
private Ollama. CouchDB and the Markdown files stay the source of truth.
Class `internal`, owner dungxbuif, status `active`.

The detailed operator runbook (reliability settings, alert thresholds, upgrade
steps, failure runbooks, rollback image digests, measured baseline) stays in
[CouchLoom on VM100](../services/couchloom.md). This page is the
standard-shaped summary; it does not replace that runbook.

## Source

| Field | Value |
|---|---|
| Local checkout | `/home/dungxbuif/workspace/projects/couchloom/` (on `codex/workspace-unreleased-20261028`, HEAD `45bd6fa`) |
| GitLab | `dungxbuif/couchloom` (default branch `main`, unverified); GitHub `dungxbuif/couchloom` |
| Repo docs | `README.md`, `ARCHITECTURE.md`, `SECURITY.md`, `llms.txt`, `docs/` (`VM100_RUNBOOK.md`, `RAG_OPERATIONS.md`, `RAG_ARCHITECTURE.md`, …) |
| Deployed revision | `9541933` ("feat(rag): add scoped retrieval and reproducible MCP evaluation"); running image `couchloom:9541933`, created 2026-10-26 |

## Internal architecture

- `couchloom` (Bun, port 8787): MCP endpoint `/mcp`, CouchDB changes-feed
  follower, pg-boss queue producer and RAG worker, `/health` `/ready` `/metrics`.
- `couchloom-postgres` (`pgvector/pgvector:0.8.6-pg17-bookworm`): pgvector index
  and the durable pg-boss queue. Must be backed up (pending/dead-letter work).
- `couchloom-ollama` (`ollama/ollama:0.40.13`): `nomic-embed-text`, 768 dims, CPU.
  Note bodies never leave VM100.
- Checkpoint advances only after durable enqueue; worker rereads the note before
  embedding; 5-minute reconciliation repairs drift. Full flow in the
  [service runbook](../services/couchloom.md#architecture-and-data-flow).

## Runtime

| Field | Value |
|---|---|
| Host / placement | VM100 `vm100-prod` |
| Stack / services | Standalone Compose project `couchloom` (not Swarm) → `couchloom`, `couchloom-postgres`, `couchloom-ollama` |
| Compose files | `compose ls` lists four: `releases/bbd500d/…/compose.yml`, `releases/9541933/…/compose.yml`, `run/knowledge-hub.network.override.yml`, `src/deploy/vm100/compose.yml` (all under `/opt/apps/couchloom/`). Use the `9541933` release path |
| Image | `couchloom:9541933` (local build, image ID `sha256:a6ec26af…`, no registry); PostgreSQL and Ollama pinned upstream images |
| Domain / exposure | None. MCP at `http://couchloom:8787/mcp` on `homelab-net`; private |
| Networks | `couchloom` on `couchloom-internal`, `homelab-net`, `knowledge-hub-net`; PostgreSQL and Ollama on `couchloom-internal` only. `couchloom-network_anchor` Swarm service keeps `homelab-net` attachable on VM100 |
| Host ports | None from the project; backup relay `10.10.0.31:15433` → CouchLoom PostgreSQL for VM110 (project `homelab-backup-db-ops-relay`) |
| Limits | app 2 CPU / 2 GiB, PostgreSQL 1 CPU / 2 GiB, Ollama 2 CPU / 4 GiB |
| Healthchecks | all three containers report `healthy` (2026-10-31) |

## Data

| Store | Name | Backup class | Last restore evidence | RPO / RTO |
|---|---|---|---|---|
| PostgreSQL 17 (VM100) | volume `couchloom_pgvector_data` | db-management worker (VM110) → Drive, receipt-level only | none recorded | not stated |
| Ollama models | Ollama volume | none (re-pullable); pre-upgrade archive `/opt/apps/homelab-backup/runs/version-upgrade-20261031/ollama/ollama-data.tgz` | n/a | n/a |
| CouchDB (Pi5, source) | LiveSync DB | Pi5 CouchDB policy; no scheduled CouchDB backup (see [STACK](../STACK.md#backups-current-reality)) | none | not stated |
| Local pre-rollout set | `/opt/apps/couchloom/run/*-20261013*` (mode 0600) | manual | none | n/a |

## Secrets

| Secret | 1Password item | Used for |
|---|---|---|
| `/opt/apps/couchloom/run/.env` (mode 0600) | (unverified) | MCP bearer/OAuth token, PostgreSQL password, runtime config |
| `/opt/apps/couchloom/run/vaults.json` (mode 0600) | (unverified) | CouchDB vault credentials |

No Swarm secrets; env-file based.

## Delivery

- CI: none found in the repo (no `.gitlab-ci.yml` or workflows).
- Deploy: manual on VM100. Create `/opt/apps/couchloom/releases/<sha>`, dump
  PostgreSQL, `docker compose … config --quiet`, build `couchloom:<sha>`,
  recreate only `couchloom`. Steps in the [service runbook](../services/couchloom.md#deployment-and-upgrade).
- Staging: none.
- Rollback: recreate `couchloom` from the retained release directory and image
  (previous releases `bbd500d`, digests listed in the
  [service runbook](../services/couchloom.md#rollback)). Never delete PostgreSQL.

## Operations

- Health: `docker exec couchloom bun -e "…fetch('http://127.0.0.1:8787/ready')…"` (no external URL).
- Logs: `docker logs couchloom` / `couchloom-ollama` / `couchloom-postgres` on VM100.
- Known issues: ambiguous four-file Compose config; production has no
  `WRITE_FOLDERS` restriction; OpenClaw registration not verified. Failure
  runbooks (Ollama, PostgreSQL, CouchDB, terminal queue jobs) in the
  [service runbook](../services/couchloom.md#failure-runbooks).

## Gate status

| Gate | State | Evidence / exception (expiry) |
|---|---|---|
| G0 Intake | fail | No `homelab-ops/stacks/couchloom/app.yml` |
| G1 Build | fail | No CI; local image, no registry digest, no scan |
| G2 Security | partial | Non-root, read-only rootfs, caps dropped, no host ports; secrets in env files, not Swarm secrets |
| G3 Runtime | fail | Manual Compose, not a CI-deployed Swarm stack |
| G4 Data | partial | Drive backup receipts via db-management; no restore recorded |
| G5 Observability | not assessed | Alert thresholds defined in runbook; no probe/scrape confirmed |
| G6 Release | not assessed | |
| G7 Docs | partial | Repo docs complete; vault doc + runbook present; revision recorded |
| G8 Operate | not assessed | |

## Recent changes

- 2026-10-31: Ollama upgraded `0.34.0` → `0.40.13`; CouchLoom smoke passed ([ledger](../deployments/version-upgrade-2026-10-31.md))
- 2026-10-26: release `9541933` built and started; steady state 1,365/1,365 documents, coverage 1
