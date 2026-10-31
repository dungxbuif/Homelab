---
type: Service
title: Knowledge Hub Search
description: Private SearXNG JSON search backend for n8n and CouchLoom on the knowledge-hub-net overlay; Compose on VM100
generated:
  by: claude-code/opus-5.5
  at: "2026-10-31T16:00:00+07:00"
stale_after: "2027-01-29T16:00:00+07:00"
lifecycle: active
project: knowledge-hub-search
class: internal
owner: dungxbuif
repo: n/a (upstream searxng/searxng)
deployed_revision: "ghcr.io/searxng/searxng@sha256:f1bbc31c7bef7a7d8dd2b105c8397eb7dea1eeb7eceebdd45c0c29aef38c0c91"
---

# Knowledge Hub Search

## Summary

`knowledge-hub-search` is a private, single-instance
[SearXNG](https://github.com/searxng/searxng) metasearch backend. It answers
JSON-only queries (Google, Bing, DuckDuckGo) for n8n "Knowledge Hub" workflows
on the private `knowledge-hub-net` overlay. It has no UI route and no public
exposure. Class `internal`, owner dungxbuif, status `active`.

This is a third-party app with no source of ours. Under the
[documentation standard §4](../standards/project-documentation.md#4-third-party-apps)
it belongs in `docs/services/`; it is kept here at the caller's request and can
be moved later.

## Source

| Field | Value |
|---|---|
| Local checkout | None. No project folder under `/home/dungxbuif/workspace/projects/` |
| Upstream | `searxng/searxng`, image `ghcr.io/searxng/searxng` pinned by digest |
| Deploy files | VM100 `/opt/apps/knowledge-hub-search/{compose.yml,settings.yml}`; env file `run/.env` (mode 0600); not tracked in `homelab-ops` (only referenced in `backup/configs-sources.json` and migration notes) |
| Repo docs | n/a (upstream docs) |
| Deployed revision | digest `sha256:f1bbc31c…` (upstream version tag unverified) |

## Internal architecture

- One container `knowledge-hub-search-knowledge-hub-search-1` (Compose profile
  `knowledge-hub`), Granian server on `:8080`, 1 worker.
- `settings.yml`: `keep_only: [google, bing, duckduckgo]`, `formats: [json]`,
  `safe_search: 1`, limiter off, `public_instance: false`, `image_proxy: false`,
  outgoing timeout 8 s (max 12 s).
- Clients on `knowledge-hub-net`: `n8n`, `n8n-runners`, `couchloom` (live
  network inspect 2026-10-31). They reach it by alias `knowledge-hub-search:8080`.
- Outbound: queries go to the upstream search engines from VM100's public IP
  (engines may rate-limit; limiter is off because the instance is private).

## Runtime

| Field | Value |
|---|---|
| Host / placement | VM100 |
| Stack / services | Compose project `knowledge-hub-search` (not Swarm); started with `--profile knowledge-hub` and `--env-file run/.env` (exact command unverified) |
| Image | `ghcr.io/searxng/searxng@sha256:f1bbc31c7bef7a7d8dd2b105c8397eb7dea1eeb7eceebdd45c0c29aef38c0c91` |
| Domain / exposure | None; private overlay only |
| Networks | External network named by `KNOWLEDGE_HUB_N8N_NETWORK`; live attachment is `knowledge-hub-net` (Swarm overlay) |
| Limits | 0.5 CPU / 512 MiB |
| Healthcheck | none |
| Logging | json-file, 5 MB × 2 |
| Host ports | none |

## Data

| Store | Name | Backup class | Last restore evidence | RPO / RTO |
|---|---|---|---|---|
| Cache volume | `search-cache` (`/var/cache/searxng`) | none (disposable) | n/a | n/a |
| Config | `compose.yml`, `settings.yml` | `homelab-ops/backup/configs-sources.json` lists it (schedule unverified); upgrade copy `/opt/apps/homelab-backup/runs/version-upgrade-20261031/searxng/` | none | config is small, rebuild by hand |

Stateless: data may be lost.

## Secrets

| Secret | 1Password item | Used for |
|---|---|---|
| `SEARXNG_SECRET` (from `/opt/apps/knowledge-hub-search/run/.env`) | (unverified) | SearXNG server secret |

Non-secret env: `KNOWLEDGE_HUB_N8N_NETWORK`, `SEARXNG_SETTINGS_PATH`, `SEARXNG_LIMITER`,
`SEARXNG_PUBLIC_INSTANCE`, `GRANIAN_*`.

## Delivery

- CI: none. Manual Compose on VM100 (Diun coverage of this image unverified).
- Upgrade: back up `compose.yml`, `settings.yml` and the old image ID, change the
  digest, `docker compose … config --quiet`, `up -d`, run a JSON search from an
  n8n container.
- Rollback: restore the previous digest `sha256:ad273460…` from
  `/opt/apps/homelab-backup/runs/version-upgrade-20261031/searxng/old-image.txt`.

## Operations

- Health: from a container on `knowledge-hub-net`,
  `http://knowledge-hub-search:8080/search?q=test&format=json` returns 200.
- Logs: `docker logs knowledge-hub-search-knowledge-hub-search-1` on VM100.
- Known issues: empty results usually mean an upstream engine is blocking or
  timing out; check logs for engine errors before changing settings.

## Gate status

| Gate | State | Evidence / exception (expiry) |
|---|---|---|
| G0 Intake | fail | No `app.yml` |
| G1 Build | not assessed | Third-party; pinned by digest, no scan record |
| G2 Security | partial | No host ports or route; secret in env file, not Swarm secret |
| G3 Runtime | fail | Manual Compose; no healthcheck |
| G4 Data | not assessed | Stateless; "data may be lost" not formally declared |
| G5 Observability | not assessed | |
| G6 Release | not assessed | |
| G7 Docs | partial | This vault doc only |
| G8 Operate | not assessed | |

## Recent changes

- 2026-10-31: image `sha256:ad273460…` → `sha256:f1bbc31c…`; JSON search 200, n8n private-network check passed ([ledger](../deployments/version-upgrade-2026-10-31.md))
- 2026-10-21: resource limits added (backup `compose.yml.bak-resource-20261021`)
