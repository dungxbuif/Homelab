# VM100 resource-cap baseline

Date: 2026-10-21  
Status: read-only baseline captured; no limits changed

## Evidence

Semaphore task `#150` (`Inspect VM100 runtime (read only)`) completed with
`ok=4`, `failed=0`, and `unreachable=0`. The VM100 observer reported 15 GiB
visible memory and 8 GiB swap. The snapshot was taken without restarting or
mutating a service.

Homepage is now bounded at 512 MiB/0.50 CPU after its canary update; its
approved image digest stayed unchanged and the public route returned HTTP 200.

Already bounded workloads include GitLab (10 GiB/4 CPU), KubeKosh (4 GiB/2
CPU), Stirling PDF (2 GiB/2 CPU), the Semaphore runner (1 GiB/1 CPU),
CouchLoom (2 GiB/2 CPU), the GitLab tunnels (128 MiB/0.5 CPU each), K8s
Syntax (128 MiB/0.25 CPU), and the pg-net anchor (16 MiB/0.05 CPU).

The following production workloads were running without a Docker limit in the
snapshot: OpenClaw, n8n, MyPocket API, MyPocket worker, macOCR proxy,
RelayHub API, RelayHub worker, NetBird server and NetBird dashboard. The
snapshot is an observation, not a safe limit recommendation by itself.

## Next controlled step

1. Capture a short canary window for one workload at a time, including request
   health, restart count, memory high-water mark and queue latency.
2. Start with low-risk stateless candidates: MezonHook, Homepage, Family Tree,
   and the NetBird dashboard. Keep the LLM/OCR/worker workloads out of the
   first batch until their peak behavior is measured.
3. Apply one Swarm service update with `start-first`, verify the public or LAN
   health contract, then record the rollback image and observed limit.

No automatic updater or broad resource change is authorized by this baseline.
