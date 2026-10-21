# Pi5 runtime audit

Date: 2026-10-21

## Collection path

The audit was executed through Semaphore's private `Homelab Audit` project,
task `#140`, using the restricted read-only observer identity. It did not use
the public VPS route and did not mutate Pi5 or the Swarm manager.

The public URL `semaphore.dungxbuif.com` intentionally remains LAN-only. From
the VPS it returns `404`; from the private Pi5 edge route it returns the
Semaphore UI and `/api/ping` returns `pong`. This is an exposure policy result,
not a broken Semaphore application.

## Observed runtime

- Pi5 is the active Swarm manager and data/edge host.
- Root filesystem: 503 GB total, 185.5 GB used, 297.4 GB free (39%).
- Memory: 7.75 GiB total, 5.65 GiB available.
- Swap: 4 GiB total, 1.66 GiB used.
- CouchDB sample: 0.73% CPU, 131.5 MiB resident memory.
- PostgreSQL sample: 1.28% CPU, 541.8 MiB resident memory, 2 GiB memory limit,
  1.5 CPU limit.
- RustFS sample: 0.02% CPU, 411.6 MiB resident memory.
- cAdvisor sample: 3.71% CPU, 84.1 MiB resident memory.

A 24-hour VictoriaMetrics range query completed after the point-in-time audit:

- CouchDB CPU: average `0.094` core, P95 `0.086` core, maximum `0.682` core
  across 289 five-minute samples.
- CouchDB working-set memory: average `140.2 MiB`, P95 `144.9 MiB`, maximum
  `145.9 MiB` across the same window.

The historical 80% CPU spike is therefore not recurring in this observation
window. cAdvisor does not expose CouchDB request-source counts; a separate
access-log/LiveSync client audit is still required before changing client
polling or rate limits.

The authenticated native CouchDB stats endpoint was also sampled. It reported
`1,040,832` cumulative HTTP requests, `544,723` GETs, `496,108` POSTs, exactly
`2` clients requesting continuous `_changes`, zero view/find/all-docs
timeouts, and zero HTTP 5xx responses. These counters confirm the two active
LiveSync streams but do not identify their source addresses or provide a
time-window delta, so no rate limit was added from this sample alone.

A follow-up native-stats delta taken 10.7 seconds apart increased the request
counter by only 2 requests (about `0.19 req/s`), with the same two continuous
change clients. Current request pressure is therefore low; historical source-IP
log analysis remains optional evidence work rather than a reason to change
production polling or rate limits.

## Follow-up spot check: 2026-10-21

The live `couchdb:3.3.3` container reported 0.40% CPU and 123.3 MiB RSS.
`/_active_tasks` was empty. A bounded 24-hour log scan found 14 `_changes`
mentions, 12 HTTP 401 responses, 3 HTTP 404 responses and no HTTP 5xx
responses. This does not show a current tight-polling incident, so no
rate-limit or LiveSync configuration change was made.

## Findings

Most Pi5 containers currently have no Docker CPU or memory limit. This includes
CouchDB, RustFS, Redis, PgBouncer, edge Traefik, AdGuard and the monitoring
containers. The current point-in-time sample is healthy, but the absence of
limits means a future workload can still starve the datastore or edge.

The audit also confirms old exited task containers remain as history, including
old Semaphore/provisioner tasks and a stopped RelayHub Compose stack. They are
not production processes, but their removal must be done through the approved
Pi manager maintenance path rather than from the VM100 worker.

## Next controlled action

1. Capture a 24-hour CPU/memory baseline from VictoriaMetrics/cAdvisor.
2. Add limits only to non-data workloads first, with one service per canary.
3. Keep PostgreSQL, CouchDB and RustFS limits conservative and change them only
   after observing working-set and IO headroom.
4. Remove exited task containers through a separately reviewed maintenance job.

## Container-history cleanup: 2026-10-21

The manager-side review found 11 stopped RelayHub Compose, Semaphore and
provisioner task containers and no `dead` containers. They were removed by ID
after checking that no running service used them. Named data volumes were
preserved, including `mypocket-prod-backups`, RelayHub NATS data and RelayHub
PostgreSQL data. The Pi5 runtime remained at 20 running containers; no service
was restarted.

No production service was restarted or reconfigured by task `#140`.
