# Swarm service inventory probe

Date: 2026-10-21
Status: source implemented; live rollout pending

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
- Live acceptance requires a successful Pi5 observer task containing a
  manager-side service list, followed by the existing drift report gate.
