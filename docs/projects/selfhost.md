---
type: Project
title: selfhost
description: Older self-hosting manifests (Docker, Kubernetes v1, VPS v1); superseded by homelab-ops
status: deprecated
generated:
  by: claude-code/opus-5.5
  at: "2026-10-31T15:00:00+07:00"
stale_after: "2027-01-29T15:00:00+07:00"
lifecycle: retired
project: selfhost
class: none
owner: dungxbuif
repo: dungxbuif/selfhost
deployed_revision: n/a
---

# selfhost

## Summary

Earlier self-hosting configs: `docker/` (argocd, authentik, certmanager,
coturn, gitlab, harbor, pgadmin, portainer, qn-office, storages, traefik,
whiteboard), `kubernetes-v1/` and `vps-v1/` (traefik, example service). The
README documents an n8n Docker/Kubernetes deployment.

## Source

| Field | Value |
|---|---|
| Local checkout | `/home/dungxbuif/workspace/projects/selfhost/` |
| GitLab | `dungxbuif/selfhost` (published branch `codex/workspace-unreleased-20261028`) |
| Repo docs | `README.md` (n8n deploy notes); no `docs/` |
| Deployed revision | n/a |

## Relation to running services

Not a deploy source for anything that runs now. Kubernetes, ArgoCD and the
Orange Pi edge are retired; current n8n, GitLab, Whiteboard and the VPS
gateway were set up outside this repo (see [STACK.md](../STACK.md)). The VPS
`coturn` and `gateway-traefik` may have started from `docker/coturn` and
`vps-v1/traefik` (unverified). Reference only; `homelab-ops` is the source
of truth.
