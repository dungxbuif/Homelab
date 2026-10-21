# Swarm service inventory probe

Date: 2026-10-21
Status: deployed and verified

## Decision

Extend the existing restricted host observer with a `swarm_services` probe.
The probe first checks `docker info` for manager capability. On a worker it
returns an explicit `{manager:false,services:[]}` result and does not call
`docker service ls`; on a manager it runs the fixed read-only `docker service
ls --format` command and returns service name, image, replicas and ports.

This closes the evidence gap in A2 without granting a Docker socket to VM100,
adding a container, or changing any service. The observer remains a fixed
forced-command SSH path and the evidence scope remains `host_runtime_only`.

## Verification

- Host observer unit tests cover the worker-safe branch and fixed command
  boundary.
- Export and runtime evidence contract tests require the new probe.
- The helper was released to Pi5 at `/usr/local/libexec/homelab-host-observer`
  with a timestamped rollback copy. The release itself did not restart a
  service or change Docker state.
- Semaphore task `#149` (`Inspect Pi5 runtime (read only)`) completed with
  `ok=4`, `failed=0`, and `unreachable=0`.
- The live report contains `swarm_services.manager=true` and a manager-side
  inventory of 25 services, including image and replica state. The Pi5
  manager evidence gap is closed.
- The scheduled VM100 target drift report remains the separate daily control;
  this probe supplies the manager-side service inventory it could not collect
  from the VM100 worker.
