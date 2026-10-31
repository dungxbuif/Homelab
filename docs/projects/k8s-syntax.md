---
type: Project
title: K8s Syntax
description: Static kubectl/YAML syntax drill app on nginx, k8s-syntax.dungxbuif.com on VM100 Swarm
generated:
  by: claude-code/opus-5.5
  at: "2026-10-31T18:00:00+07:00"
stale_after: "2027-01-29T18:00:00+07:00"
lifecycle: lab
project: k8s-syntax
class: lab
owner: dungxbuif
repo: dungxbuif/k8s-syntax
deployed_revision: af8481e
---

# K8s Syntax

## Summary

Static training app for practising `kubectl` commands, quick config, YAML
fields and output syntax. Question bank and a kubectl v1.36.1 option catalog
are bundled; attempts and reports are kept in browser LocalStorage
(`k8s-syntax-v1`). No backend, no cluster. Split out of the Obsidian vault.
Class `lab`, owner dungxbuif, status `lab`.

## Source

| Field | Value |
|---|---|
| Local checkout | `/home/dungxbuif/workspace/projects/k8s-syntax/` (branch `main`, HEAD `af8481e`) |
| GitLab | `dungxbuif/k8s-syntax` (default branch `main`) |
| Repo docs | `README.md` (Vietnamese), `DEPLOYMENT.md` |
| Deployed revision | `af8481e` (image tag; image built 2026-09-24 01:45 +07, one minute after the commit) |

## Internal architecture

- Plain ES modules: `src/app.mjs`, `engine.mjs`, `questions.mjs`, `kubectl-catalog.mjs`; tests `node --test tests/*.test.mjs`.
- `Dockerfile`: single stage `nginx:1.29-alpine`, copies the repo into the web root, writes `/healthz`; `.mjs` served with `no-cache`.
- nginx master runs as root (stock image).

## Runtime

| Field | Value |
|---|---|
| Host / placement | VM100 (`node.hostname==vm100-prod`), amd64 |
| Stack / services | No stack. Standalone Swarm service `k8s-syntax` 1/1 (created 2026-09-23, spec updated 2026-10-20) |
| Image | `homelab/k8s-syntax:af8481e` (`sha256:9b4237ee…`) — **local-only image on VM100**, no registry |
| Domain / exposure | `k8s-syntax.dungxbuif.com` · **public** (200 via VPS on 2026-10-31; Pi5 router has no `lan-only` middleware) → `tasks.k8s-syntax:80` |
| Networks | `edge-http-net` (repo `DEPLOYMENT.md` and runtime policy still say `homelab-net`) |
| Limits | 0.25 CPU / 128 MiB limit, 32 MiB memory reservation |
| Update config | `stop-first`, `failure_action: pause` (not rollback), monitor 5s |
| Healthcheck | `wget http://127.0.0.1/healthz` every 30s |

## Data

| Store | Name | Backup class | Last restore evidence | RPO / RTO |
|---|---|---|---|---|
| none | stateless; user progress in browser LocalStorage | n/a ("data may be lost") | n/a | rebuild image from git |

## Secrets

None.

## Delivery

- CI: none. Image built by hand on VM100 tagged with the commit sha.
- Staging: none. Prod: `docker service update --image homelab/k8s-syntax:<sha> k8s-syntax` from Pi5.
- Rollback: update back to the previous sha tag if still in the VM100 image cache (previous documented tag `1921819`, presence unverified).

## Operations

- Health: `https://k8s-syntax.dungxbuif.com/healthz` (200, 2026-10-31).
- Logs: `docker service logs k8s-syntax` (Pi5).
- Stale JS after a release → assets are `no-cache`; bump the asset version (as in `af8481e`).

## Gate status

| Gate | State | Evidence / exception (expiry) |
|---|---|---|
| G0 Intake | fail | No `app.yml`; class `lab` allows only `lan`/`private`, but the route is public |
| G1 Build | fail | No CI; local-only image; runs as root |
| G2 Security | partial | No secrets, no host ports; public exposure not intended for `lab` |
| G3 Runtime | fail | Hand-created service, no stack, `failure_action: pause` |
| G4 Data | pass | Declared stateless; data may be lost |
| G5 Observability | not assessed | Healthcheck only; probe unverified |
| G6 Release | not assessed | Not required for `lab` |
| G7 Docs | partial | README + DEPLOYMENT.md; DEPLOYMENT.md image/network are stale and name lab internals |
| G8 Operate | not assessed | |

Fix options for G0: add `lan-only` to the Pi5 router and remove the name from
the VPS HostSNI list, or re-class the app as `public`.

## Recent changes

- 2026-10-20: service spec updated (network moved to `edge-http-net`, inferred from live spec).
- 2026-09-24: image `af8481e` (cache-busted module scripts).
- 2026-09-23: Swarm service `k8s-syntax` created on VM100.
