---
type: Project
title: Homepage
description: Static nginx bookmark page for the self-hosted tools, served at dungxbuif.com from Swarm on VM100
generated:
  by: claude-code/opus-5.5
  at: "2026-10-31T18:00:00+07:00"
stale_after: "2027-01-29T18:00:00+07:00"
lifecycle: active
project: homepage
class: public
owner: dungxbuif
repo: dungxbuif/homepage
deployed_revision: 01299fe7da4bb18aa3350b2fe39769da1bfea69e
---

# Homepage

## Summary

A single static `index.html` (a `tools` array of links to self-hosted apps)
served by nginx. It is the public landing page at `dungxbuif.com`. It holds no
data and no secrets. Class `public`, owner dungxbuif, status `active`.

## Source

| Field | Value |
|---|---|
| Local checkout | `/home/dungxbuif/workspace/projects/homepage/` |
| GitLab | `dungxbuif/homepage` (private project 5, default branch `main`) |
| Repo docs | `README.md` (Vietnamese), `docs/automation-delivery.md` |
| Deployed revision | `01299fe` (GitLab main, exported from reviewed local `d80d43e`); local HEAD `939f493` adds docs only |

Local branches `archive/pre-automation-main` and `codex/automation-delivery`
are recovery history, not deploy branches.

## Internal architecture

- `nginx:alpine` pinned by digest (`sha256:df221db8…`, nginx 1.31.6), `COPY index.html`. No build step.
- Image healthcheck `wget http://127.0.0.1/`.
- CI runs on the restricted rootless GitLab runner 1 (locked to projects 2 and 5).
- Release to prod is a separate Semaphore job (`homepage-release.yml`) that SSHes to Pi5 as the restricted user `homelab-homepage-release` and runs the root-owned helper `homepage-release <digest>`. The helper writes a receipt and the playbook posts it to Mezon.
- Catalog entry: `homelab-ops/automation/stacks/catalog.yml` id `homepage` (`deployable: true`, release template 6).

## Runtime

| Field | Value |
|---|---|
| Host / placement | VM100 (`node.hostname==vm100-prod`) |
| Stack / services | No stack. Standalone Swarm service `homepage` (created 2026-09-15, last spec update 2026-10-21) |
| Image | `registry-gitlab.dungxbuif.com/dungxbuif/homepage@sha256:c128afca4e026cfc4f33d4cf1c77adc8cb08f01215a3f2bde76a1ecca12b79fd` |
| Domain / exposure | `dungxbuif.com`, `www.dungxbuif.com` · public (VPS HostSNI → Rathole → Pi5 Traefik → `tasks.homepage:80`) |
| Networks | `edge-http-net` |
| Limits | 0.5 CPU / 512 MiB limit, no reservation |
| Update config | parallelism 1, `start-first`, `failure_action: rollback`, monitor 30s |
| Healthcheck | `wget -qO- --timeout=3 http://localhost:80/` every 30s |

## Data

| Store | Name | Backup class | Last restore evidence | RPO / RTO |
|---|---|---|---|---|
| none | stateless; content is in the image | n/a | n/a | rebuild from git / previous image |

## Secrets

None at runtime. CI uses GitLab predefined `CI_REGISTRY_*` job variables. The
release playbook needs the Semaphore Variable Group `HOMELAB_MEZON_WEBHOOK_URL`
(1Password item path unverified).

## Delivery

- CI: `.gitlab-ci.yml` job `build:homepage` (docker 27.5.1 + rootless dind): build `linux/amd64`, `scripts/smoke-image.sh` (byte compare + `nginx -t`), push `$CI_REGISTRY_IMAGE:$CI_COMMIT_SHA`, emit `HOMEPAGE_IMAGE=<digest>` in `release.env`. Does not include `platform/ci-templates`; no Trivy.
- Staging: none. Prod: Semaphore "homepage release" template (digest fixed in the playbook vars), manual.
- Rollback: Swarm auto-rollback on failed update; manual rollback via Semaphore rollback spec or previous image `homelab/homepage:vm100-20261007-stirling` (local-only, from catalog).

## Operations

- Health: `https://dungxbuif.com/` (200 public and LAN, checked 2026-10-31).
- Logs: `docker service logs homepage` (from Pi5).
- Adding a tool: edit the `tools` array in `index.html`, push, wait for the pipeline digest, update the release playbook digest, run the Semaphore release.
- Known issues: `docker service ps` shows one Failed task 5 days ago next to the running one (cause unverified; VM100 node event likely shared by every VM100 service).

## Gate status

| Gate | State | Evidence / exception (expiry) |
|---|---|---|
| G0 Intake | partial | Repo on GitLab, catalog entry; no `stacks/homepage/app.yml` |
| G1 Build | partial | Green pipeline 39/job 83, amd64, digest pinned. Missing: ci-templates, Trivy, SBOM, cosign; nginx master runs as root |
| G2 Security | partial | No secrets, no host ports. Renovate not configured (unverified) |
| G3 Runtime | fail | Hand-created service, no stack, no reservations |
| G4 Data | pass | Stateless; nothing to restore |
| G5 Observability | not assessed | Healthcheck exists; blackbox probe/Mezon alert unverified |
| G6 Release | partial | Semaphore release with receipt; no semver tag, no staging |
| G7 Docs | partial | README + one doc; no `docs/configuration.md`, `CHANGELOG.md` |
| G8 Operate | not assessed | |

## Recent changes

- 2026-10-21: service spec updated (network/edge migration window; detail unverified).
- 2026-10-15: first AMD64 publication from GitLab pipeline 39/job 83 (`01299fe`), digest `c128afca…`.
