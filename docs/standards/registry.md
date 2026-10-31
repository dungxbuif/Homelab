---
type: Decision
title: Container Registry Decision
description: One registry for the whole lab — GitLab Container Registry (storage on RustFS) serves every image, our own and third-party; the Pi5 registry is deleted
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

**One registry for the whole lab: GitLab Container Registry (`registry-gitlab.dungxbuif.com`).** Every image that runs in the lab, our own and third-party, is pulled from it. The Pi5 `registry:2` (`registry.dungxbuif.com`) is deleted, with no mirror and no second registry. The RustFS bucket is only its storage, not another registry.

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
- Third-party images (traefik, postgres, n8n, …) are copied into the same registry under `dungxbuif/mirror/<upstream-path>` by a CI job (`skopeo copy --all`, digest preserved) whenever Renovate bumps them. Stacks reference the copy, never Docker Hub or ghcr directly. Docker Hub images may instead use GitLab's built-in Dependency Proxy, which is still the same registry.

## Required to promote it from "trial" (plan P4)

1. Move storage to RustFS and enable the metadata DB and online GC (above). Set a cleanup policy per project.
2. Back up the bucket and record one restore test.
3. Make split DNS and the Pi5 route for `registry-gitlab.dungxbuif.com` work from the LAN, so pulls do not hairpin through the VPS. Create a read-only deploy token for Swarm.
4. Push every local-only image (table above) and re-pin the services by digest (P0.5).
5. Move MyPocket to GitLab Registry, then delete `registry.dungxbuif.com` (archive its 1.5 GiB to Drive first).
6. Copy the third-party images in use into `dungxbuif/mirror/` and repin the stacks.

## Third-party images in the same registry

| Source | How it enters the lab registry |
|---|---|
| Docker Hub | CI mirror job, or the GitLab Dependency Proxy (`registry-gitlab.dungxbuif.com/dungxbuif/dependency_proxy/containers/...`) |
| ghcr.io, quay.io, docker.stirlingpdf.com, … | CI mirror job `mirror:<image>`, triggered by the Renovate MR that bumps the digest |

Policy gate: an image reference outside `registry-gitlab.dungxbuif.com` fails the MR. The only exception is the break-glass rebuild of GitLab itself (§Risk accepted).

## Risk accepted

With one registry, GitLab is a dependency for every pull. If GitLab is down, running tasks keep their cached images and nothing stops. Only new deploys and re-pulls wait.
- GitLab itself (and anything needed to rebuild it) is pulled from upstream, pinned by digest. This is the break-glass exception.
- Because the blobs live in RustFS on Pi5, a rebuilt GitLab reattaches to the bucket and every image is still there.
- GitLab is protected as described in the [GitLab protection plan](../superpowers/plans/2026-10-31-gitlab-protection-and-registry-consolidation.md).
