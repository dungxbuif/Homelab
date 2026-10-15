# Runtime resource audit

Semaphore tasks 30 (VM100) and 31 (Pi5) succeeded through the existing restricted
observer on 2026-10-15 around 01:11 UTC. These are point-in-time observations,
not load tests or proof of peak capacity. Rootless CI, VPS and Mac are excluded.

| Host | RAM total | RAM available | Swap used/total | Root filesystem |
| --- | --- | --- | --- | --- |
| VM100 | 15.61 GiB | 8.05 GiB | 27.2 MiB / 8 GiB | 71% used, about 57.9 GiB available |
| Pi5 | 7.75 GiB | 5.02 GiB | 1.84 GiB / 4 GiB | 39% used, about 278.8 GiB available |

Pi swap occupancy alone does not prove current pressure: available RAM remains
substantial. Do not clear caches or swap just to make utilization look lower.
VM100's observed largest containers include GitLab 3.80 GiB (10 GiB reported
ceiling), KubeKosh 1.05 GiB (4 GiB), Stirling 835.5 MiB (2 GiB), OpenClaw
693.6 MiB and n8n 630.9 MiB. Pi PostgreSQL uses 445.2 MiB (2 GiB reported
ceiling); RustFS uses 622.6 MiB. Many other reported ceilings equal host RAM.

## Next collection change

Add a fixed resource-limit probe to the restricted observer. Use only validated
container IDs already collected, and a fixed Docker inspect format selecting
ID/name and HostConfig memory, memory reservation/swap, NanoCpus, CPU quota/
period, CPU shares and PID limit. Never emit full inspect, environment, labels,
mounts or command arguments. Propagate missing/failed inventory as incomplete
collection; never turn an unknown limit into zero/unlimited. Keep timeouts and
the clean environment. Tests must verify selection boundaries, identifier
validation and failure handling before installing via the existing enrollment
playbook. Then run fresh Semaphore audits for authoritative configured limits.
No app limits, networks or public documentation change in this read-only audit.

## Configured limits verified

The helper was enrolled via Ansible on both hosts, changing only the helper.
Semaphore task 37 (VM100) and task 36 (Pi5) completed successfully with the
selected-field resource-limit probe. Only running container IDs are counted:

- VM100: 27 running containers, 18 with no explicit memory or CPU hard limit.
- Pi5: 22 running containers, 21 with no explicit memory or CPU hard limit.
- Rootless CI remains outside this rootful-Docker collection.

| VM100 component | Memory hard limit | CPU hard limit | Memory reservation |
| --- | --- | --- | --- |
| Semaphore executor | 1 GiB | 1 CPU | 0 |
| GitLab HTTPS tunnel | 128 MiB | 0.5 CPU | 0 |
| GitLab registry tunnel | 128 MiB | 0.5 CPU | 0 |
| GitLab SSH tunnel | 128 MiB | 0.5 CPU | 0 |
| GitLab | 10 GiB | 4 CPU | 0 |
| k8s-syntax | 128 MiB | 0.25 CPU | 0 |
| Stirling PDF | 2 GiB | 2 CPU | 0 |
| CouchLoom app | 2 GiB | 2 CPU | 0 |
| KubeKosh | 4 GiB | 2 CPU | 1 GiB |

On Pi, shared PostgreSQL is limited to 2 GiB and 1.5 CPU, with zero reservation.
All observed running containers returned a null container PID limit. These are
container settings, not a claim that host/user cgroups impose no other limits.

The VM's configured memory ceilings sum to 19.5 GiB before its 18 unlimited
containers and rootless CI are counted. Ceilings are not allocations: this does
not prove current exhaustion, but simultaneous peaks can exhaust host memory.
Do not arbitrarily shrink GitLab/PostgreSQL or clear swap to hide this risk.
Next gates are peak working-set/CPU/PSI/OOM observation during existing backup,
CI and representative app workloads, then per-app measured limits/reservations
with one-at-a-time validation and rollback. Do not claim high-load acceptance.

## Collector verification and limitations

The probe validates container identifiers and uses a fixed inspect template;
it never returns general inspect output. It runs immediately after inventory
to minimize the container-churn window. Failed commands keep collection
incomplete, with only an allowlisted diagnostic hint, never raw stderr.

VM tasks 32, 34 and 35 failed the new inspect probe with exit 1. Subsequent
direct diagnostics and task 37 succeeded. Container churn is plausible but
the root cause is not proven; retain those failed tasks and do not claim this
race is eliminated. Pi tasks 33 and 36 succeeded. The final diagnostic-hint
helper revision was reconciled on Pi after task 36; it changes failure reporting,
not successful fields. Both hosts retain the existing forced-command boundary.

Ten focused observer tests and the full 50-test automation Python suite pass;
review found no blockers. Live success is a bounded point-in-time resource
observation, not application health, network acceptance or backup certification.

## Short workload observation

Seven read-only `/proc` samples per host, ten seconds apart, were taken while
retention PID 1133089 remained active. VM100's window was 01:54:10-01:55:10 UTC;
Pi's was 01:59:28-02:00:28. These are separate one-minute windows, not a peak
load test or proof that backup and CI overlapped for every sample. Pipeline 55
had finished its builds and pipeline 56's validation job was observed running.

| Measurement | VM100 | Pi5 |
| --- | --- | --- |
| Available RAM range | 8.00-8.19 GiB | 5.12-5.21 GiB |
| Load average (1 min) range | 6.53-7.96 | 0.35-0.60 |
| Swap-in delta | 0 pages | 3 pages |
| Swap-out delta | 0 pages | 0 pages |
| OOM kill counter delta | 0 | 0 |
| Memory PSI full delta | about 0.055% of window | 0 |
| CPU PSI some delta | about 16.4% | about 0.86% |
| I/O PSI full delta | about 15.7% | about 0.38% |

PSI is stall time, not CPU utilization or disk throughput. These observations
do not support increasing RAM merely to reduce swap occupancy. VM100 shows
CPU/I/O contention worth profiling through a complete build/backup cycle before
raising concurrency or imposing new per-app limits. Pi had no measured memory
stall or swap-out in its sample. No caches were dropped, swap cycled, load
generated, or resource limits changed. Sustained per-app peak acceptance remains
open; existing container limits/uncapped workloads still require reconciliation.
