---
type: Decision
title: Container Registry Decision
description: GitLab Container Registry becomes the single lab registry; the Pi5 registry becomes a pull-through mirror for tier-1 images
status: draft
generated:
  by: claude-code/opus-5.5
  at: "2026-10-31T14:00:00+07:00"
stale_after: "2027-01-29T14:00:00+07:00"
---

# Container Registry Decision

## Current state (2026-10-31)

| Registry | Where | Used by | Problem |
|---|---|---|---|
| `registry.dungxbuif.com` (`registry:2`) | Pi5 standalone container | MyPocket api/web/worker | No per-project auth or cleanup policy, an old image line, no scanning |
| `registry-gitlab.dungxbuif.com` (GitLab Registry, labelled "trial") | Inside the VM100 GitLab Omnibus, local disk | homepage, db-management, provisioner, semaphore-runner | Still labelled trial, no scheduled backup, metadata DB off, storage on the VM100 disk |
| No registry (local images) | VM100 / Pi5 Docker cache only | macocr-proxy, mezonhook, openclaw, k8s-syntax, relayhub-v1, relayhub-admin, couchloom, whiteboard-*, rathole | Lost if the node dies, and Swarm cannot reschedule them |

## Decision

**GitLab Container Registry is the only registry for app images in the lab.** The Pi5 registry stays, but only as a **pull-through mirror** for tier-1 infrastructure images.

Reasons:

- Auth is per project, and CI pushes with `CI_JOB_TOKEN`. No extra credentials have to be managed.
- Cleanup policies and project visibility are already built in, and images sit next to the pipeline that built them.
- It is already in use by 4 workloads, so no new system has to be introduced.
- Alternatives rejected:
  - Harbor: heavy, several containers, and retired once already in the K8s era.
  - A cloud registry: adds an external dependency and egress for every pull.

## Required to promote it from "trial" (plan P4)

1. Enable the registry metadata database and online garbage collection. Set a cleanup policy per project: keep the last 10 tags plus every tag that matches `v*`.
2. Add a backup class for registry data (or move storage to RustFS S3 with versioning) and record one restore test.
3. Make split DNS and the Pi5 route for `registry-gitlab.dungxbuif.com` work from the LAN, so pulls do not hairpin through the VPS.
4. Push every local-only image (table above) and re-pin the services by digest.
5. Move MyPocket to GitLab Registry, then stop pushing to `registry.dungxbuif.com`.

## Pi5 mirror (tier T1)

- Replace `registry:2` with a pull-through cache (`distribution` in proxy mode, or `zot` with sync).
- It mirrors only the images Pi5 needs in order to come back without VM100: traefik, rathole, adguard, postgres, pgbouncer, redis, couchdb, rustfs and the monitoring images.
- Docker daemons on Pi5 and VM100 use it as `registry-mirrors`.

## Risk accepted

GitLab lives on VM100 (tier T3). If VM100 is down, new app images cannot be pulled. Running tasks keep their cached image, and Pi5 tier-1 services still recover from the mirror. Rebuilding VM100 restores the registry from its backup.
