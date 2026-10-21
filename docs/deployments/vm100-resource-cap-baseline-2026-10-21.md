# VM100 resource-cap baseline

Date: 2026-10-21  
Status: controlled canaries in progress

## Evidence

Semaphore task `#150` (`Inspect VM100 runtime (read only)`) completed with
`ok=4`, `failed=0`, and `unreachable=0`. The VM100 observer reported 15 GiB
visible memory and 8 GiB swap. The snapshot was taken without restarting or
mutating a service.

Homepage is now bounded at 512 MiB/0.50 CPU after its canary update; its
approved image digest stayed unchanged and the public route returned HTTP 200.
The macOCR proxy is now bounded at 1 GiB/1 CPU; its image stayed unchanged and
both `/healthz` and `/readyz` returned HTTP 200 after the stop-first update.
The n8n service is now bounded at 2 GiB/1 CPU; its task became healthy after
the expected warm-up and `/healthz` returned HTTP 200. OpenClaw is now bounded
at 2 GiB/1 CPU with `stop-first`; its task became healthy after warm-up and
`/`, `/healthz`, and `/readyz` returned HTTP 200. During the OpenClaw restart,
the public route briefly returned 502 while the task was starting; no rollback
was needed. MyPocket API is now bounded at 1 GiB/1 CPU with `stop-first`;
`/api/v1/health` returned HTTP 200 after warm-up. Its worker remains uncapped
until queue latency and memory high-water marks are captured. RelayHub API and
worker are now each bounded at 1 GiB/1 CPU in their persistent Compose source;
`/readyz`, `/healthz`, and `/docs/` returned HTTP 200 after recreate. RelayHub
NATS and Redis were recreated by Compose but their persistent volumes were
retained and their limits remain unchanged.

Already bounded workloads include GitLab (10 GiB/4 CPU), KubeKosh (4 GiB/2
CPU), Stirling PDF (2 GiB/2 CPU), the Semaphore runner (1 GiB/1 CPU),
CouchLoom (2 GiB/2 CPU), the GitLab tunnels (128 MiB/0.5 CPU each), K8s
Syntax (128 MiB/0.25 CPU), and the pg-net anchor (16 MiB/0.05 CPU).

The following production workloads were running without a Docker limit in the
snapshot: MyPocket worker, NetBird server and NetBird dashboard. MyPocket API
and RelayHub API/worker are now capped. NetBird dashboard is now capped at
512 MiB/0.50 CPU with `start-first`; its public dashboard returned HTTP 200.
NetBird server remains uncapped because it owns persistent control-plane state.
The snapshot is not a safe limit recommendation for the remaining workloads
by itself.

## Next controlled step

1. Capture a short canary window for one workload at a time, including request
   health, restart count, memory high-water mark and queue latency.
2. Continue with one service at a time. Stateful or socket-owning services use
   `stop-first`; stateless services may use `start-first` when capacity allows.
3. Apply one Swarm service update, verify the public or LAN health contract,
   then record the rollback image and observed limit. Do not cap workers until
   queue latency and memory high-water marks are captured.

No automatic updater or broad resource change is authorized by this baseline.
