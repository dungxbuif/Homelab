---
type: Reference
title: Homelab Overview and Operating Rules
description: Code ownership, topology summary and the operating constraints every operator and agent must follow
generated:
  by: claude-code/opus-5.5
  at: "2026-10-31T16:00:00+07:00"
stale_after: 2026-11-30 00:00:00+07:00
tags:
- overview
- rules
---

# Homelab Overview and Operating Rules

## Code ownership

Infrastructure code (Compose/Swarm stacks, Ansible, OpenTofu, CI, Semaphore
templates) lives in `/home/dungxbuif/workspace/projects/homelab-ops`. Make code
changes there, never in this vault. After a deployment, record the observed
result, resource allocation, rollback path and `homelab-ops` revision here.
Legacy checkouts and worktrees from the earlier code migration are being
retired; do not use them.

## Topology

![Homelab system overview](/docs/assets/diagrams/system-overview.svg)


```text
Public HTTPS -> VPS Traefik -> Rathole :7000 -> Pi5 Traefik
             -> Swarm overlays -> VM100 apps / Pi5 HTTP services
GitLab web/registry trial -> VPS Traefik -> Rathole 7002/7003 -> VM100 GitLab
Git SSH -> VPS :2222 -> Rathole 7001 -> VM100 GitLab :22
Apps -> Pi5 PostgreSQL/PgBouncer, Redis, CouchDB, RustFS (private Docker DNS)
OCR: Mac worker -> outbound WSS -> VM100 macocr-proxy
LLM: VPS :18123 -> Mac Rathole client -> LM Studio :1234
```

## Operating constraints

1. Read STATUS.md and the relevant runbook before changing infrastructure;
   record intended behaviour and verification first, reconcile docs after,
   and log significant decisions in [log.md](/docs/log.md).
2. Pi5 is the datastore and Swarm manager; production compute is VM100;
   VM110 runs db-management only. VM100 is production, not a lab VM. Audit
   Proxmox before any cleanup or IaC destroy.
3. Deploy portless services on private overlays. Pi5 Traefik uses
   file-provider routes, not Swarm labels. GitLab's VPS labels are a separate
   exception.
4. No home-router port forwards. New host-port exceptions need an explicit
   purpose and approval.
5. Secrets live in ignored `local_vars.json`, `credentials/`, deployed private
   files, Swarm secrets or 1Password. Never print or commit secret values.
6. No credential changes, raw SQL mutations, destructive cleanup or
   production restarts without explicit operator approval.
7. `projects/mac-ocr/` source is read-only for behaviour changes. Pi5 images
   must be `linux/arm64`; VM100/VM110 images `linux/amd64`.
8. Project checkouts live under `/home/dungxbuif/workspace/projects/`
   (see [PROJECTS.md](/docs/PROJECTS.md)); checkout location is not
   deployment placement.
9. GitLab stateful updates must not overlap tasks sharing a bind mount: back
   up, scale to zero, confirm exit, then start the replacement
   ([GitLab runbook](/docs/services/gitlab.md)).
