---
type: Service
title: Semaphore
description: Semaphore UI (Ansible runner) on the Pi5 with a remote runner on VM100; retiring in IaC plan P1
generated:
  by: claude-code/opus-5.5
  at: "2026-10-31T15:00:00+07:00"
stale_after: "2027-01-29T15:00:00+07:00"
lifecycle: active
class: internal
owner: dungxbuif
deployed_revision: v2.19.17
---

# Semaphore

## Summary

Semaphore UI runs operator templates (homepage release, DB provisioning via
the provisioner, host audits). **Retiring:** the [IaC plan](../superpowers/plans/2026-10-31-lab-iac-automation-rebuild.md)
phase P1 replaces it with GitLab CI jobs and then removes it. Do not add new
templates. Third-party app; class `internal`, status `active` (retiring).

## Source

| Field | Value |
|---|---|
| Upstream | https://github.com/semaphoreui/semaphore |
| Pinned version | `semaphoreui/semaphore:v2.19.17@sha256:008dacd9…` (stack label still `v2.19.12` → updated by hand) |
| Runner image | `registry-gitlab.dungxbuif.com/dungxbuif/homelab-automation/semaphore-runner@sha256:157f469f…` (our build) |
| Deploy source | Swarm stacks `semaphore`, `semaphore-executor`; stack files in `homelab-ops` |

## Internal architecture

UI/API on the Pi5 with SQLite; tasks run on the remote runner
`semaphore-executor_runner` on VM100 (`SEMAPHORE_USE_REMOTE_RUNNER`). Templates
call `homelab-provisioner`. Template config is manual in the UI.

## Runtime

| Field | Value |
|---|---|
| Placement | UI on Pi5 (`rpivn`); runner on VM100 |
| Services | `semaphore_semaphore`, `semaphore-executor_runner` |
| Domain / exposure | `semaphore.dungxbuif.com`, LAN-only (Pi5) |
| Networks | runner: `homelab-control-net`; UI (unverified) |
| Limits | UI 1 CPU / 1 GiB; runner 1 CPU / 1 GiB (reservation 0.1 CPU / 128 MiB) |
| Healthcheck | none on either |

## Data

| Store | Name | Backup class | Last restore evidence | RPO / RTO |
|---|---|---|---|---|
| SQLite (bind) | `/ssd-data/infra/semaphore/data` (Pi5) | none | none | not stated |
| Bind | `/ssd-data/infra/semaphore/{playbooks,repository}` | none | n/a | rebuildable |

## Secrets

Swarm secrets: `semaphore_admin_password`, `semaphore_access_key_encryption`,
`homelab_provisioner_token`, `semaphore_runner_<id>`. 1Password paths (unverified).

## Delivery

- Manual image updates ([version-upgrade-2026-10-31](../deployments/version-upgrade-2026-10-31.md)).
- **Retirement (P1):** tar the SQLite data to Drive → `docker stack rm semaphore semaphore-executor`
  → remove the route/rewrite → delete `semaphore_*` secrets and data after 30 days.

## Operations

- Logs: `docker service logs semaphore_semaphore` (Pi5)
- Known issue: CI job `validate:semaphore-bootstrap` points at a missing file.

## Gate status

| Gate | State | Evidence / exception (expiry) |
|---|---|---|
| G0 Intake | not assessed | retiring |
| G1 Build | partial | images pinned by digest |
| G2 Security | partial | Swarm secrets used; LAN-only |
| G3 Runtime | fail | stack drift, no healthchecks |
| G4 Data | fail | SQLite not backed up |
| G5 Observability | not assessed | |
| G6 Release | not assessed | |
| G7 Docs | partial | this doc |
| G8 Operate | not assessed | retirement planned in P1 |

## Recent changes

- 2026-10-31: upgraded to `v2.19.17`; BACKLOG U7 (no-op task receipt) partial.
