---
type: Project
title: "<Project name>"
description: "<one line: what it is and where it runs>"
generated:
  by: human:dungxbuif | claude-code/opus-5.5
  at: YYYY-MM-DDTHH:MM:SS+07:00
stale_after: <generated.at + 90 days>
tags: [project]
project: <folder name under workspace/projects>
class: lab | internal | public | none
lifecycle: active | lab | paused | retired | not deployed
owner: dungxbuif
repo: <gitlab group/project>
deployed_revision: <git sha or tag, or "n/a">
---

# <Project name>

## Summary

<What it does, for whom, and why it runs in the lab.>

## Source

| Field | Value |
|---|---|
| Local checkout | `/home/dungxbuif/workspace/projects/<project>/` |
| GitLab | `dungxbuif/<project>` (default branch `<main>`) |
| Repo docs | `<repo>/README.md`, `<repo>/docs/` |
| Deployed revision | `<sha/tag>` |

## Internal architecture

<Components, internal dependencies, and anything intentionally left out of the public docs.>

## Runtime

| Field | Value |
|---|---|
| Host / placement | <VM100 / VM110 / Pi5> |
| Stack / services | `homelab-ops/stacks/<app>/` → `<stack>_<svc>` |
| Image | `registry-gitlab.dungxbuif.com/...@sha256:...` |
| Domain / exposure | `<host>` · public / lan / private |
| Networks | `edge-http-net`, `<app>-net`, ... |
| Limits | CPU / memory |

## Data

| Store | Name | Backup class | Last restore evidence | RPO / RTO |
|---|---|---|---|---|
| PostgreSQL | `<db>` | `<class>` | `<date + record>` | `<24h / 1h>` |

## Secrets

| Secret (Swarm) | 1Password item | Used for |
|---|---|---|
| `<app>_db_url_v1` | `homelab-prod/apps/<app>/db` | database connection |

## Delivery

- CI: `<pipeline / template>`
- Staging: `<auto / none>`. Prod: MR + manual `deploy:<app>:prod`
- Rollback: revert the prod digest MR (previous digest `<...>`)

## Operations

- Health: `<url>`
- Logs: `docker service logs <stack>_<svc>` (from the Pi5 manager)
- Known issues: <symptom → fix>

## Gate status

| Gate | State | Evidence / exception (expiry) |
|---|---|---|
| G0 Intake | not assessed | |
| G1 Build | not assessed | |
| G2 Security | not assessed | |
| G3 Runtime | not assessed | |
| G4 Data | not assessed | |
| G5 Observability | not assessed | |
| G6 Release | not assessed | |
| G7 Docs | not assessed | |
| G8 Operate | not assessed | |

## Recent changes

- YYYY-MM-DD: <change> (`<revision>`)
