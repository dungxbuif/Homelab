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
