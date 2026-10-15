# Network membership audit through Semaphore

Read-only Semaphore tasks 38 (VM100, observed 02:23:15 UTC) and 39 (Pi5,
02:23:31 UTC) completed successfully with `collection_complete=true` and no
probe errors. Evidence is Docker rootful container membership, not a traffic
test or proof of firewall isolation. Rootless CI, VPS and Mac are outside scope.

## Observed boundaries

- VM100: 28 running containers at collection time, including the transient
  `vigorous_napier` diagnostic. Sixteen attach to `homelab-net`.
- Pi5: 22 running containers, including active Restic check `a60abd9136f2`.
  Ten attach to `homelab-net`. Do not treat the temporary Restic task as an
  undeclared permanent application or remove it during retention.
- Homepage, Family Tree and Mezonhook use `edge-http-net` only. n8n uses
  `edge-http-net` plus `data-net`.
- RelayHub worker/NATS/Redis use `relayhub-net` only; its API additionally uses
  `homelab-net`. CouchLoom PostgreSQL/Ollama use `couchloom-internal` only;
  its app additionally uses `homelab-net`.
- BDS Cloudflare connector uses only `bds-tunnel-net`, as required. BDS app
  uses that network plus `homelab-net`.
- Semaphore and its executor use only `homelab-control-net`. Provisioner also
  joins `homelab-net`, so the control plane as a whole is not fully isolated.
- MyPocket API/worker each join `data-net`, `homelab-net`, `mypocket-net` and
  `mypocket-redis-net`. Network presence alone does not identify active consumers.

Pi publishes PostgreSQL gateway 5432, Redis 16379, AdGuard 53/81,
Alertmanager 9093, VictoriaMetrics 8428 and Traefik 80/443 on all host interfaces
as reported by Docker. This is not proof of Internet reachability: firewall,
NAT, NetBird and VPS ingress must be checked independently. Other entries such
as `5432/tcp` without a host mapping are exposed container ports only.

## Catalog reconciliation and next gates

Record exact observed runtime names for logical IDs that differ from service or
container names. Use `runtime_service` for Swarm services and `runtime_container`
for standalone containers; never bind policy identity to ephemeral task IDs.
Validate the policy and existing tests after the metadata-only correction.

Private-network rollout remains incomplete. Before changing each app, resolve
its actual DNS/upstream dependencies, produce an approved exact deployment diff
and rollback, then test ingress and required data paths after migration. Do not
detach `homelab-net` across all apps in one operation. Static apps are candidates
for early rollout but still require the managed apply boundary and route tests.

No network, host port or container was modified by these jobs. Internal docs and
catalog metadata change; public application docs do not because behavior does
not change. Inventory completeness remains false.
