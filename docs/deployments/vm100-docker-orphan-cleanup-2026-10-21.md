# VM100 Docker orphan cleanup

Date: 2026-10-21

## Scope

Remove only Docker objects that are provably unreferenced by every current or
stopped container. Production data volumes, named backup volumes, tagged
rollback images, and recent Swarm task records remain untouched.

## Evidence

Before cleanup, VM100 reported 12 dangling volumes. Eleven had the Docker
`com.docker.volume.anonymous` label and no container reference. Their combined
payload was about 1.3 GiB. The named volume `mypocket-prod-backups` was also
dangling, but was retained because its name indicates an intentional backup
target and it has no anonymous-volume label.

The cleanup removed the eleven anonymous volumes only. It did not use
`docker system prune --volumes`.

Post-cleanup:

- dangling volumes: only `mypocket-prod-backups`
- Docker volumes: 10 total, 9 active, 440.8 MiB logical size
- Docker build cache: 7.437 GiB reclaimable, but no cache older than the
  seven-day maintenance window was present
- filesystem `/`: 31 GiB free, 85% used

## Decision

No further automatic volume deletion is justified. The remaining disk pressure
is dominated by GitLab backup data, images/build cache, and Docker/containerd
accounting rather than anonymous volumes. Future maintenance must preserve
named data and backup volumes and should remove build cache only after a clear
age threshold or an explicit release window.

## Verification

The following checks passed after cleanup:

```text
docker system df
df -h /
docker volume ls -qf dangling=true
```

The Swarm service inventory was not changed by this cleanup.

## Maintenance policy decision

The deployed daily maintenance unit is now the accepted policy for B6:

- remove images and BuildKit entries only when older than seven days;
- retain at least 5GB of BuildKit cache when Docker supports the setting;
- never prune volumes automatically;
- skip or warn on a hung `docker system df` report without turning safe cleanup
  into a failed run.

The 2026-10-21 recheck reclaimed `0B`, which is the expected safe result when
the apparent reclaimable cache is recent or still referenced.

## Follow-up image review

The VM100 image inventory was checked after the volume cleanup. One old
NetBird server image (`sha256:308653...`, about 303 MiB) had no container
reference; the active NetBird server uses a different digest. The old image was
removed. Images for the active `kubekosh`, `k8s-syntax`, Ollama, n8n runner,
NetBird and Semaphore services were retained. The post-removal Docker report
showed 116 images and 43.99 GiB logical image size.

The filesystem sample fluctuated to 29 GiB free / 86% used after this change,
so the disk-pressure item remains open. This small image removal is not a
substitute for the separate GitLab backup retention and rollback-image review.

## Maintenance recheck

On 2026-10-21 the constrained maintenance action was run again with
`docker builder prune --filter until=168h`. It reclaimed `0B`: the reported
7.437 GiB of logical BuildKit reclaimable space is still recent or referenced
and must not be removed by an age-blind prune. VM100 remained at 30 GiB free
and 85% used. No image, container, volume or service was changed by this
recheck.
