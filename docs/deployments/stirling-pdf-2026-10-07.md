# Stirling-PDF Public Deployment - 2026-10-07

## Current edge reconciliation (2026-10-13)

The deployment record below captures the original rollout and intentionally
keeps its historical Orange Pi wording. The active edge is now the Pi5
standalone `edge-traefik-pi5`; the current image, replica state, and route
boundary are recorded in the [runtime inventory](./runtime-inventory-2026-10-13.md).
The service remains VM100, portless, and pinned to Stirling `3.1.0`.

## Decision

Deploy Stirling-PDF as a portless Docker Swarm service on VM100 and publish it
through the existing Orange Pi Traefik file provider at
`https://stirling.dungxbuif.com/`. The service will use the fixed official
image tag `3.1.0`, attach only to `homelab-net`, and keep its configuration,
OCR data, pipeline files, and logs on VM100 bind mounts.

The deployment does not add a database or a host-published port. Login is
enabled before public exposure and the initial administrator credential is
kept outside Git. The service has explicit resource and Docker log limits so
it cannot reproduce the current unbounded GitLab JSON log problem.

## Homepage change

Add a `Stirling PDF` shortcut to the existing static Homepage source on VM100,
then rebuild and update the `homepage` Swarm service. The shortcut points to
the public URL and remains a normal external link; Homepage does not proxy the
application.

## Affected flow

```text
public browser
  -> VPS Rathole
  -> Orange Pi Traefik file provider
  -> homelab-net Swarm DNS: tasks.stirling-pdf:8080
  -> VM100 Stirling-PDF task
```

## Verification plan

- Confirm the Swarm task is `1/1`, healthy, constrained to `vm100-prod`, and
  has no published host port.
- Probe Stirling over the overlay network and through the public HTTPS hostname.
- Verify TLS, login page, and the Homepage shortcut from the public root.
- Confirm persistent directories exist and are writable by the container.
- Confirm the Traefik source/live dynamic configuration hashes and route target.
- Record the final image digest, resource limits, and rollback details here.

## Deployment evidence

- VM100 task is `1/1`, healthy, constrained to `vm100-prod`, and has no
  published host port.
- Official image pulled and pinned at digest
  `sha256:b5b9e400c086e5334a4947a0d7cd589808f743f29267d7f41c18200cf4bc48b4`.
- Overlay probe to `http://tasks.stirling-pdf:8080/api/v1/info/status`
  returned `{"version":"3.1.0","status":"UP"}`.
- LAN edge HTTPS probe to `https://stirling.dungxbuif.com/` and `/login`
  returned `200`; DNS resolves to the Orange Pi edge (`10.10.0.5`) on LAN.
- Homepage was rebuilt as `homelab/homepage:vm100-20261007-stirling`; the
  public root contains the `Stirling PDF` shortcut.
- Traefik live config was backed up to
  `/home/dungxbuif/edge/traefik/dynamic.yml.bak-stirling-20261007` and the
  live file now targets `http://tasks.stirling-pdf:8080`.
- Initial admin password is stored outside Git at
  `/opt/apps/stirling-pdf/admin-password` on VM100 with mode `600`.

## Remaining public-edge action

The VPS gateway currently returns `404` when the hostname is forced directly
to `103.82.21.202`, while the Orange Pi edge route returns `200`. This means
the VPS `/root/gateway/dynamic.yml` TCP `HostSNI` allow-list still lacks
`stirling.dungxbuif.com`. The VPS SSH agent was unavailable during deployment,
so that single allow-list change remains pending; no VPS file was overwritten.

## Rollback

On VM100, update the service back to the previous Homepage image if the
shortcut needs to be reverted:

```sh
docker service update --image homelab/homepage:vm100-20260910 homepage
```

For Stirling, remove the service only after preserving the bind-mounted
`/opt/apps/stirling-pdf` directory. Restoring the Traefik backup removes the
edge route; the backup must be copied into the live file path, not renamed over
the bind-mounted inode.

## Resource note

Before deployment VM100 had 6 vCPU, 9.7 GiB available RAM, 60 GiB free disk,
and 8 GiB swap. Disk pressure was found in Docker JSON logs (GitLab task log
about 16 GiB) and systemd journal (about 3.8 GiB). These are not deleted as
part of this deployment; they need a separate maintenance window with an
explicit log-rotation and Docker metadata cleanup plan.
