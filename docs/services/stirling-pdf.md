---
type: Service
title: Stirling PDF
description: Stirling PDF toolkit, Swarm service on VM100 at stirling.dungxbuif.com
generated:
  by: claude-code/opus-5.5
  at: "2026-10-31T15:00:00+07:00"
stale_after: "2027-01-29T15:00:00+07:00"
lifecycle: active
class: internal
owner: dungxbuif
deployed_revision: 3.1.0
---

# Stirling PDF

## Summary

Self-hosted PDF tools (merge, split, OCR, convert). Third-party app; class
`internal` (unverified intake), status `active`.

## Source

| Field | Value |
|---|---|
| Upstream | https://github.com/Stirling-Tools/Stirling-PDF |
| Pinned version | `docker.stirlingpdf.com/stirlingtools/stirling-pdf:3.1.0@sha256:b5b9e400…` |
| Deploy source | none: `docker service create`, no stack in `homelab-ops` |

## Internal architecture

Single stateless container; OCR language data in `tessdata`. No database.

## Runtime

| Field | Value |
|---|---|
| Host / placement | VM100 (`node.hostname==vm100-prod`) |
| Service | `stirling-pdf` |
| Domain / exposure | `stirling.dungxbuif.com` → `tasks.stirling-pdf:8080` (exposure unverified) |
| Networks | `edge-http-net` |
| Limits | 2 CPU / 2 GiB; reservation 0.25 CPU / 512 MiB |
| Healthcheck | none |
| Update | `failure_action: pause` (not rollback) |

## Data

| Store | Name | Backup class | Last restore evidence | RPO / RTO |
|---|---|---|---|---|
| Bind mounts | `/opt/apps/stirling-pdf/{configs,customFiles,logs,pipeline,tessdata}` | none | none | data may be lost (config only) |

## Secrets

None. Env names only: `SECURITY_ENABLELOGIN`, `SYSTEM_MAXFILESIZE`, etc. Whether
login is enabled is (unverified) — check before treating as authenticated.

## Delivery

- Manual `docker service update --image` from the Pi5.
- Rollback: `docker service rollback stirling-pdf`.

## Operations

- Health: `https://stirling.dungxbuif.com/` (no app healthcheck configured)
- Logs: `docker service logs stirling-pdf`; app logs also in `/opt/apps/stirling-pdf/logs`

## Gate status

| Gate | State | Evidence / exception (expiry) |
|---|---|---|
| G0 Intake | fail | no `app.yml` |
| G1 Build | partial | upstream image pinned by digest |
| G2 Security | not assessed | admin/login state unverified |
| G3 Runtime | fail | no stack, no healthcheck, `failure_action: pause` |
| G4 Data | not assessed | config-only data |
| G5 Observability | not assessed | |
| G6 Release | not assessed | |
| G7 Docs | partial | this doc |
| G8 Operate | not assessed | |
