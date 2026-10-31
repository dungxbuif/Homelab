---
type: Decision
title: Container Registry Decision
description: One registry for the whole lab — GitLab Container Registry on the dedicated GitLab VM serves every image, our own and third-party; the Pi5 registry is deleted
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

## Storage: local disk on the GitLab VM (decided 2026-10-31)

Because GitLab gets its own VM (VM120), the registry keeps **filesystem storage on that VM's disk**. RustFS was considered and rejected as the primary store.

Why local disk:

- Fewer moving parts: no S3 credentials, no `s3_v2` config, and no dependency on Pi5 RustFS for every push and pull.
- Pi5 is already the single datastore host, and RustFS has no backup schedule yet (B0). Putting the registry there would make Pi5 more critical.
- Images are rebuildable. Our images come from CI tags, and third-party images can be re-copied from upstream. A lost registry is slow to rebuild, not data loss.
- GitLab, its database and its registry form **one unit**, backed up and restored together.

Design:

| Item | Value |
|---|---|
| Path | Omnibus default (`/var/opt/gitlab/gitlab-rails/shared/registry`) on VM120, sized in the [compute plan](../superpowers/plans/2026-10-31-compute-layout-and-sizing.md) (disk 150 GiB) |
| Size control | Registry metadata database (bundled PostgreSQL) + online GC + cleanup policy (keep the last 10 tags, every `v*` tag and every deployed digest). Target: under 25 GiB |
| Backup | Daily restic (incremental, deduplicated, encrypted) of the registry directory → RustFS `gitlab-backups` (in-lab copy on another host) + Google Drive. `gitlab-backup` runs with `SKIP=registry` so the native archive stays small. Weekly `vzdump` of VM120 |
| Restore | Restore the directory with restic, then run a registry metadata check. The monthly drill pulls one digest |

**Fallback:** if the Proxmox thin pool cannot hold VM120's disk (step R0 of the compute plan), use RustFS S3 storage instead (`s3_v2`, bucket `gitlab-registry`, path-style, scoped key).

## Image lifecycle (fully automated)

```text
CI build → push :<sha> (CI_JOB_TOKEN) → Trivy + SBOM + cosign → digest
→ bot MR env/stg.yml → Swarm pulls by digest (read-only deploy token, --with-registry-auth)
→ tag vX.Y.Z adds a tag to the SAME digest → bot MR env/prod.yml → policy verifies registry + digest + signature
→ weekly cleanup policy + online GC → nightly restic backup of the registry directory → drift flags any image outside the registry
```

- Only CI pushes; humans have no push rights. Tags are `<sha>` and `vX.Y.Z`. `latest` is never used.
- Cleanup policy: keep the last 10 tags, every `v*` tag and every digest that is currently deployed.
- Third-party images (traefik, postgres, n8n, …) are copied into the same registry under `dungxbuif/mirror/<upstream-path>` by a CI job (`skopeo copy --all`, digest preserved) whenever Renovate bumps them. Stacks reference the copy, never Docker Hub or ghcr directly. Docker Hub images may instead use GitLab's built-in Dependency Proxy, which is still the same registry.

## Required to promote it from "trial" (plan P4)

1. Move GitLab (with its registry) to VM120, then enable the metadata DB and online GC. Set a cleanup policy per project.
2. Back up the registry directory (restic → RustFS + Drive) and record one restore test.
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
- The registry is restored together with GitLab from restic and `vzdump`. Our images can also be rebuilt from git tags.
- GitLab is protected as described in the [GitLab protection plan](../superpowers/plans/2026-10-31-gitlab-protection-and-registry-consolidation.md).
