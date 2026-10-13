# Homelab Infrastructure

Current architecture: **v3.3, VM100 compute + Pi5 edge/datastore + Mac service tunnel**.
Canonical repository: `/Users/dungxbuif/workspace/homelab`.
Documentation audited on 2026-09-16; verification coverage is recorded in
[the audit report](./docs/research/docs-stack-audit-2026-09-16.md).

## Start Here

- [Current stack and network catalog](./docs/STACK.md): workloads, domains,
  database endpoints, ingress exceptions, and proposed versus deployed work.
- [Core documentation index](./docs/INDEX.md): host and service runbooks.
- [System operations](./docs/MAIN.md): edge configuration and export workflow.
- [Changelog](./docs/LOG.md) and [archive](./docs/archived/INDEX.md): history,
  not current deployment instructions.
- [Backup and restore runbook](./docs/runbooks/backup-restore.md): native
  backup commands, mandatory post-checks, Mezon reporting, and Drive retention.
- [CouchLoom second-brain runbook](./docs/services/couchloom.md): VM100
  topology, local embedding/RAG reliability, security, backup, rollback, and
  the SSH-to-automation roadmap.
- [Agent-readable navigation](./llms.txt): plain Markdown entry points.

## Current Topology

```text
Public HTTPS -> VPS Traefik -> Rathole :7000 -> Pi5 Traefik
             -> homelab-net -> VM100 apps / Pi5 HTTP services

GitLab web/Registry trial -> VPS Traefik -> isolated Rathole pairs
                         -> VM100 clients -> GitLab :80 / :5005
Git SSH -> VPS :2222 -> isolated Rathole -> VM100 GitLab :22

BDS -> dedicated Cloudflare connector -> bds-app (private bds-tunnel-net)
VM100 apps -> Pi5 PostgreSQL/PgBouncer and Redis (private Docker DNS)
OCR -> VM100 macocr-proxy -> Mac Rathole tunnel -> native OCR :8787
LLM -> Mac Rathole tunnel -> LM Studio :1234
```

VM100 app host ports `18080/18081/18084/18085` are retired, not current
upstreams. The GitLab Registry is **trial-only**; the Pi5 registry remains
production. Mac OCR/LLM roaming uses the local Rathole client in
`/Users/dungxbuif/dev-env/mac-service-tunnel`; NetBird remains proposed for
private administration and ACL-based access.

## Operational Constraints

1. Read this entry point and relevant runbook before changing infrastructure.
   Record intended behavior and verification before implementation, reconcile
   docs afterward, and append significant decisions to the changelog.
2. Keep Pi5 as the datastore and Swarm manager; place production application
   compute on VM100. VM100 `100` is production, not a disposable AWS lab VM.
   VMs `101/102` were removed per the migration record; audit hypervisor state
   before any cleanup or IaC destroy.
3. Deploy portless Docker services using private service DNS. The active Pi5
   edge currently uses **file-provider routes**, not automatic Swarm labels.
   VPS GitLab Docker labels are a separate local-provider exception.
4. Do not add home-router public forwards. New host-port exceptions require
   an explicit purpose and approval; retain approved datastore/native LAN
   ports and existing public tunnel control/SSH ports only as documented.
5. Secrets belong in ignored `local_vars.json`, `credentials/`, deployed
   private files or Swarm secrets. Never print or commit secret values.
   Check the exact application/runtime source; do not assume local vars
   are the only credential store or rewrite that file casually.
6. No credential changes, raw SQL/engine mutations, destructive cleanup, or
   production restarts without explicit operator approval. Preserve unrelated
   worktree changes. Prefer manifests and supported APIs.
7. `projects/mac-ocr/` source is read-only for behavior changes; use approved
   build/deployment mechanisms. Pi5 images must support `linux/arm64`;
   VM100 images must support `linux/amd64`.
8. MyPocket source remains `/Users/dungxbuif/workspace/MyPocket/`; do not move
   it. Its production web/API/worker **are deployed on VM100**. Project
   checkout placement is not deployment placement.
9. GitLab stateful updates must not overlap tasks sharing the same bind
   mount. Back up DB/config/data, scale to zero, confirm the old container
   exited, then start the replacement; see its service runbook.

## Verification Limits

VM100 inventory and selected public routes were rechecked during this audit.
Pi5/VPS direct-key SSH did not authenticate; their host inventories were not
refreshed. Orange Pi SSH timed out before banner exchange. Public HTTP checks
do not establish authenticated workflows, NetBird remote-peer connectivity,
CI execution, off-host backup, or restore readiness.

[Older entry point](./docs/archived/superseded-topology/index-before-docs-audit-20260916.md)
is preserved for historical context only.
