---
type: Decision
title: Container Registry Decision
description: GitLab Container Registry is the single lab registry with its storage on RustFS (Pi5); the Pi5 registry becomes a pull-through mirror for tier-1 images
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

## Storage: RustFS S3 on Pi5 (decided 2026-10-31, plan only)

Registry blobs move from the VM100 disk (`/opt/apps/gitlab/data/gitlab-rails/shared/registry`, **14 GiB** on 2026-10-31) to a RustFS bucket on Pi5. RustFS has 264 GiB free and already sits on the private `s3-net` overlay.

Why:

- Registry data then lives in tier T1 (Pi5), next to the other datastores. A rebuilt GitLab on any VM attaches to the same bucket and every image is still there.
- It frees VM100 disk (66% used), and the registry gets object versioning and the RustFS backup class.

Design:

| Item | Value |
|---|---|
| Bucket | `gitlab-registry`. Versioning on. Lifecycle rule: expire noncurrent versions after 7 days |
| Access | A dedicated access key scoped to this bucket only. Kept in 1Password `homelab-prod/platform/gitlab-registry-s3` and passed to GitLab as a Swarm secret |
| GitLab config | `registry['storage'] = { 's3_v2' => { regionendpoint: 'http://rustfs:9000', bucket: 'gitlab-registry', pathstyle: true, region: 'us-east-1' } }`. GitLab reaches RustFS over `s3-net` |
| Metadata DB | Registry metadata database `gitlab_registry` on Pi5 PostgreSQL, created by `db_provision`. Enables online GC |
| Backup | The bucket is enrolled in the RustFS backup class and depends on BACKLOG B0, because RustFS has no schedule today |

Migration (one maintenance window, nothing is deleted):

1. Back up the GitLab config and registry directory, and record the list of image digests in use.
2. Create the bucket, key and metadata DB through the normal provisioning job.
3. Put the registry in read-only mode, then `mc mirror` the filesystem storage into the bucket.
4. Switch `gitlab.rb` to `s3_v2`, run the metadata import, reconfigure, and leave read-only mode.
5. Pull every recorded digest from VM100 and from Pi5. Deploy one app on staging as a smoke test.
6. Keep the old directory read-only for 14 days, then delete it in a separate approved job.
7. Rollback: switch the config back to filesystem storage. The old directory is unchanged until step 6.

## Image lifecycle (fully automated)

```text
CI build → push :<sha> (CI_JOB_TOKEN) → Trivy + SBOM + cosign → digest
→ bot MR env/stg.yml → Swarm pulls by digest (read-only deploy token, --with-registry-auth)
→ tag vX.Y.Z adds a tag to the SAME digest → bot MR env/prod.yml → policy verifies registry + digest + signature
→ weekly cleanup policy + online GC → nightly backup of the bucket → drift flags any image outside the registry
```

- Only CI pushes; humans have no push rights. Tags are `<sha>` and `vX.Y.Z`. `latest` is never used.
- Cleanup policy: keep the last 10 tags, every `v*` tag and every digest that is currently deployed.
- Third-party images are pulled through the Pi5 mirror, pinned by digest, and bumped by Renovate MRs.

## Required to promote it from "trial" (plan P4)

1. Move storage to RustFS and enable the metadata DB and online GC (above). Set a cleanup policy per project.
2. Back up the bucket and record one restore test.
3. Make split DNS and the Pi5 route for `registry-gitlab.dungxbuif.com` work from the LAN, so pulls do not hairpin through the VPS. Create a read-only deploy token for Swarm.
4. Push every local-only image (table above) and re-pin the services by digest (P0.5).
5. Move MyPocket to GitLab Registry, then stop pushing to `registry.dungxbuif.com`.

## Pi5 mirror (tier T1)

- Replace `registry:2` with a pull-through cache (`distribution` in proxy mode, or `zot` with sync).
- It mirrors only the images Pi5 needs in order to come back without VM100: traefik, rathole, adguard, postgres, pgbouncer, redis, couchdb, rustfs and the monitoring images.
- Docker daemons on Pi5 and VM100 use it as `registry-mirrors`.

## Risk accepted

The GitLab registry *service* still runs on VM100 (tier T3). If VM100 is down, new app images cannot be pulled. Running tasks keep their cached image, and Pi5 tier-1 services still recover from the mirror. Because the blobs live in RustFS on Pi5, a rebuilt GitLab reattaches to the bucket without restoring image data.
