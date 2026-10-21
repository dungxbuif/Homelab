# Diun image watch

Date: 2026-10-21

## Decision

Use Diun as a notify-only Docker image watcher on VM100. It checks the images
of running containers every 12 hours and sends a warning to the existing Mezon
hook when an update is detected. It never pulls, recreates, restarts, or
redeploys an application.

The image is pinned to:

```text
crazymax/diun@sha256:e324b793eb32dfb7f74d3a39421ebf090141caaadee69b8f78da63112408ee25
```

## Runtime boundary

- Host: VM100, `/opt/apps/diun`
- Container: `homelab-diun`
- Docker socket: read-only mount, used only for image discovery
- No published ports and no application network attachment
- Persistent state: `/opt/apps/diun/data`
- Secret: existing `/etc/homelab-backup/secrets/mezon-webhook`, mounted read-only
- Limits: `0.25 CPU`, `256 MiB`; read-only root filesystem and `no-new-privileges`

The watcher uses `watchByDefault: true` for running containers, so newly
deployed containers are covered without editing every application stack. Image
updates remain an explicit operator decision through the existing GitLab and
Semaphore release path.

## Verification result

The release gate passed on VM100:

1. `docker compose config` succeeded;
2. `homelab-diun` is healthy and has no published port;
3. the running image reports Diun `v4.33.0` and the configured 12-hour Docker
   scan started successfully;
4. the mounted Mezon notification script returned `rc=0` for a sanitized
   synthetic update event without exposing the webhook URL;
5. CPU and memory limits are `250000000` nanocpus and `268435456` bytes.

One expected warning was observed for the local-only `couchloom` image, which
is named like a Docker Hub image but is not published there. It does not affect
the watcher or notification path and should be excluded with an explicit
`diun.enable=false` label when the CouchLoom source compose is next reconciled.

Rollback is `docker compose down` from `/opt/apps/diun`; the data directory
can be retained for a later re-enable.
