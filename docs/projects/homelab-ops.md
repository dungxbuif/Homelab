---
type: Project
title: homelab-ops
description: "Central ops repository: Ansible, Swarm stacks, routes, backup contracts, automation image and CI for the lab"
generated:
  by: claude-code/opus-5.5
  at: "2026-10-31T16:00:00+07:00"
stale_after: "2027-01-29T16:00:00+07:00"
lifecycle: active
project: homelab-ops
class: internal
owner: dungxbuif
repo: dungxbuif/homelab-ops
deployed_revision: n/a (per-artifact; origin/main 871cfd5, local work on codex/workspace-unreleased-20261028 80e56ed)
---

# homelab-ops

## Summary

`homelab-ops` is the infrastructure project, not an end-user app. It owns
deployment manifests, host automation (Ansible, OpenTofu for Proxmox VM
lifecycle), the route catalog and generated edge files, backup contracts,
secret *references*, release verification and rollback. Application repos own
source, tests and images; this vault owns topology, runbooks and evidence only.
It is the target home of every `stacks/<app>/app.yml` in the
[App Delivery Gates](../standards/app-delivery-gates.md). Class `internal`,
owner dungxbuif, status `active`, but most live services still predate it
(see [STACK](../STACK.md)).

## Source

| Field | Value |
|---|---|
| Local checkout | `/home/dungxbuif/workspace/projects/homelab-ops/` (on `codex/workspace-unreleased-20261028`, HEAD `80e56ed`, 2026-10-28) |
| GitLab | `dungxbuif/homelab-ops` (default branch `main`, `origin/main` = `871cfd5`, 2026-10-24). CI pushes images under `dungxbuif/homelab-automation/*` (project rename or alias, unverified) |
| Repo docs | `README.md` (Vietnamese, partly historical K8s/ArgoCD), `automation/README.md`, `automation/stacks/README.md`, `docs/{deployments,migrations,superpowers}` |
| Deployed revision | Varies per artifact; record per app in its own vault doc |

## Internal architecture

| Path | Role |
|---|---|
| `automation/policies/active-runtime.yaml`, `retired-runtime.yaml` | Active and retired runtime inventory (no secrets) |
| `automation/ansible/` | Inventories, playbooks, roles: bootstrap, enrollment, host ops, app deploys (db-management) |
| `automation/tofu/` | Proxmox VM lifecycle (`proxmox`, `proxmox-db-ops`) |
| `automation/routes/` | `catalog.yml` + schemas → `generated/pi5-traefik.yml` (Pi5 file provider) and VPS fragments |
| `automation/stacks/` | `catalog.yml`; `db-management/` (stack, `versions.lock.json`, runbook) is the only adopted app stack |
| `automation/execution-environment/` | Pinned toolchain image (Ansible, OpenTofu, Docker CLI, ShellCheck) |
| `automation/semaphore/`, `provisioner/` | Private control plane: Semaphore stack and the `homelab-provisioner` service |
| `automation/backup-runner/`, `rustfs-backup/`, `gitlab-backup/`, `couchdb-backup-proxy/` | Backup jobs and relays (e.g. `db-ops-relay.compose.yml` → VM100 project `homelab-backup-db-ops-relay`) |
| `automation/diun/`, `maintenance/`, `rustdesk-gateway/` | Host utilities |
| `backup/` | Legacy backup contracts kept during cutover |
| `monitoring/`, `edge-registrar/`, `migration/` | Monitoring config, edge registration, migration artifacts |
| `k8s/`, `argocd-apps/`, `archive/` | Historical; Kubernetes is not part of the lab. Do not execute |

Operating rule: an agent proposes a Git change or starts an approved Semaphore
job; the runner executes with a restricted credential. Agents get no general
host SSH keys, Docker socket or DB credentials.

## Runtime

Artifacts from this repo running in the lab (live 2026-10-31):

| Field | Value |
|---|---|
| Host / placement | Pi5 (Semaphore, provisioner), VM110 (db-management), VM100 (backup relay, diun, network anchor) |
| Stack / services | `semaphore_semaphore` (`semaphoreui/semaphore:v2.19.17@sha256:008dacd9…`), `semaphore-executor_runner` (`…/homelab-automation/semaphore-runner@sha256:157f469f…`), `homelab-provisioner_provisioner` (`…/homelab-automation/provisioner@sha256:c7b60154…`), `db-management` stack, `couchloom-network_anchor` (`alpine@sha256:d9e853e8…`) |
| Image registry | `registry-gitlab.dungxbuif.com/dungxbuif/homelab-automation/{automation-ee,semaphore-runner,provisioner}` by digest |
| Domain / exposure | Semaphore LAN-only `semaphore.dungxbuif.com`; provisioner internal `homelab-net:8787`, no route |
| Networks | `homelab-net`, `homelab-control-net` (per service, unverified) |
| Limits | not assessed |

## Data

| Store | Name | Backup class | Last restore evidence | RPO / RTO |
|---|---|---|---|---|
| Git | GitLab repo `dungxbuif/homelab-ops` | GitLab (no scheduled GitLab backup) + workstation checkout | none | not stated |
| Semaphore DB | (unverified) | (unverified) | none | not stated |

The repo itself is the recovery source for manifests; uncommitted local work
on `codex/workspace-unreleased-20261028` is not mirrored until pushed.

## Secrets

The repo holds secret names and references only; CI runs a tracked-file secret
pattern scan. CI variables (names): `OPS_DEPLOY_ENABLED` (gate), registry
credentials via `CI_REGISTRY*`. Runtime secrets for adopted stacks are listed
in each app doc (for example [db-management](./db-management.md#secrets)).
1Password paths: (unverified).

## Delivery

- CI: `.gitlab-ci.yml`, stages `validate` → `build` → `deploy`.
  - `validate:semaphore-bootstrap`, `validate:automation-ee`, `validate:experimental-ee`: YAML, shell syntax, runtime policy, ansible-lint, tofu fmt, secret patterns, route/app contracts.
  - `build:automation-ee`, `build:semaphore-runner-candidate`, `build:provisioner` (arm64): push by commit SHA, print digest.
  - `deploy:homepage-production`: manual, only when `OPS_DEPLOY_ENABLED == "true"` on the default branch or a tag; otherwise never.
- App repos (db-management) fetch a reviewed `OPS_REF` of this repo to validate their deploy contract.
- Rollback: revert the MR and rerun the deploy job, or redeploy the previous digest recorded in the stack lock.

## Operations

- Health: no service of its own; check Semaphore UI and `docker service ls` on Pi5.
- Logs: GitLab pipeline logs; `docker service logs semaphore-executor_runner`.
- Known issues: README still describes the K8s/ArgoCD path; `origin/main` is behind local work; most lab services are not yet adopted into `stacks/` (plan P0.5/P5 in the [IaC rebuild plan](../superpowers/plans/2026-10-31-lab-iac-automation-rebuild.md)).

## Gate status

| Gate | State | Evidence / exception (expiry) |
|---|---|---|
| G0 Intake | not assessed | Infrastructure repo; gates apply to the artifacts it ships |
| G1 Build | partial | Own images built in CI and referenced by digest; scan gate not seen |
| G2 Security | partial | Secret-pattern scan in `validate`; Renovate not seen |
| G3 Runtime | not assessed | |
| G4 Data | not assessed | |
| G5 Observability | not assessed | |
| G6 Release | not assessed | |
| G7 Docs | partial | README outdated (K8s path); automation README current |
| G8 Operate | not assessed | Nightly drift report not yet generated from this repo |

## Recent changes

- 2026-10-28: CloudBeaver clean workspace and TCP healthcheck in db-management stack (`80e56ed`, local branch)
- 2026-10-26: homelab ops source-of-truth boundary documented (`01a8570`, local `main`, not yet on `origin/main`)
- 2026-10-24: Ansible uses the Pi5 operator account for manager delegation (`871cfd5`, `origin/main`)
