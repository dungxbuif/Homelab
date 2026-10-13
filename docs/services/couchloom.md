# CouchLoom on VM100

## Purpose and current status

CouchLoom is the private, headless access layer for the Markdown second brain.
Obsidian Self-hosted LiveSync writes the source documents to CouchDB; CouchLoom
turns those documents into an authenticated MCP surface for agents and maintains
a local semantic index. It does not replace Obsidian, CouchDB, or the Markdown
files as the source of truth.

Production was last validated on **2026-10-13** on VM100 (`10.10.0.31`). The
running CouchLoom release is Git commit/image tag `8f7a8e0`, stored as the
immutable release `/opt/apps/couchloom/releases/8f7a8e0`. The corresponding
hardening and documentation changes are merged into the local CouchLoom `main`
branch at `f5e322c`.

| Field | Current value |
| --- | --- |
| Host | VM100 `vm100-prod`, `10.10.0.31` |
| Runtime | Standalone Docker Compose, not a Swarm stack |
| MCP endpoint | `http://couchloom:8787/mcp` on `homelab-net` |
| Source of truth | Existing CouchDB LiveSync database on `homelab-net` |
| Vector and queue store | `pgvector/pgvector:0.8.6-pg17-bookworm` |
| Embedding runtime | `ollama/ollama:0.34.0`, CPU on VM100 |
| Embedding model | `nomic-embed-text`, 768 dimensions |
| Host/public ports | None |
| Current steady state | 1,357/1,357 documents, 6,074 chunks, coverage 1, backlog 0, failed 0 |
| Runtime health | CouchLoom, PostgreSQL, and Ollama healthy; zero restarts at validation |

The model remains hosted on VM100. Note bodies are embedded through the private
`couchloom-ollama:11434` endpoint and are not sent to an external embedding
provider.

## Architecture and data flow

```text
Obsidian devices
      |
      | Self-hosted LiveSync
      v
CouchDB on homelab-net  <---------------- source of truth
      |
      | acknowledged changes feed
      v
CouchLoom metadata index -- MCP --> OpenClaw and other authenticated agents
      |
      | durable pg-boss enqueue
      v
PostgreSQL/pgvector queue --> reread current note --> local Ollama embedding
      |                                                |
      +---------------- pgvector index <---------------+
                               |
                               +--> semantic search over MCP
```

Only `couchloom` joins both networks. PostgreSQL and the long-running Ollama
server are isolated on the private `couchloom-internal` bridge. CouchLoom joins
the existing attachable `homelab-net` to reach CouchDB and to serve MCP clients.
No service publishes a host port.

The changes-feed checkpoint advances only after work has been durably enqueued
in PostgreSQL. The worker rereads the current document immediately before
embedding, so an old event cannot overwrite a newer edit. Startup reconciliation
and a non-overlapping five-minute reconciliation loop repair missing, stale,
model-mismatched, empty, and orphaned vector records. Duplicate delivery is
safe. Metadata reads remain available when Ollama or the RAG worker is down.

## Security boundary

- MCP requires a bearer/OAuth token. Secrets and CouchDB vault credentials live
  in mode-`0600` files under `/opt/apps/couchloom/run` and are never committed.
- The application runs as the non-root `bun` user with a read-only root
  filesystem, `init`, all Linux capabilities dropped, `no-new-privileges`, and
  a 64 MiB `noexec,nosuid` `/tmp` tmpfs.
- CouchLoom is limited to 2 CPU and 2 GiB RAM. Its only persistent writable
  application path is the managed `/data` volume.
- PostgreSQL, Ollama, MCP, health, readiness, and metrics have no host or public
  listener. Access is through private Docker networking.
- The MCP tool catalog supports read/list/search plus note creation and editing.
  Delete, move, and rename are deliberately absent.
- Production currently has no `WRITE_FOLDERS` restriction, so authenticated
  create/edit operations may target any path in the configured vault. Use
  `READ_ONLY=true` or configure `WRITE_FOLDERS` before granting a less-trusted
  agent access.
- Metrics use bounded vault/state labels and must never contain note paths,
  bodies, search queries, tokens, or credentials.

## Reliability policy

PostgreSQL stores both the derived pgvector index and the durable pg-boss queue.
Vectors can be rebuilt from CouchDB, but PostgreSQL must still be backed up so
pending and dead-letter work survives recovery.

| Setting | Production/default | Operational meaning |
| --- | ---: | --- |
| `RAG_RETRY_LIMIT` | `10` | attempts before dead-letter |
| `RAG_RETRY_DELAY_SECONDS` | `1` | initial retry delay |
| `RAG_RETRY_DELAY_MAX_SECONDS` | `900` | exponential-backoff cap |
| `RAG_JOB_HEARTBEAT_SECONDS` | `30` | active-job heartbeat |
| `RAG_JOB_EXPIRE_SECONDS` | `3600` | hard bound for legitimate long CPU jobs |
| `RAG_QUEUE_SUPERVISE_INTERVAL_SECONDS` | `30` | expired-claim scan interval |
| `RAG_DATABASE_CONNECT_TIMEOUT_MS` | `5000` | bounded queue reconnect attempt |
| `RAG_RECONCILE_INTERVAL_MS` | `300000` | drift-repair interval |
| `RAG_WORKER_CONCURRENCY` | `1` | simultaneous embedding jobs |
| `RAG_SHUTDOWN_GRACE_MS` | `30000` | graceful queue shutdown bound |

Do not lower the one-hour job bound without measuring the largest notes. A
production batch legitimately exceeded five minutes on CPU Ollama; the
30-second heartbeat and supervisor detect abandoned workers separately.

## Health and observability

`/health`, `/ready`, and `/metrics` are private endpoints. `/ready` returns HTTP
200 while the core metadata service is usable, including when RAG is
backfilling or degraded. HTTP 503 means the core vault service is unavailable.

| RAG state | Meaning | Expected action |
| --- | --- | --- |
| `ready` | coverage complete, no backlog or terminal failure | none |
| `backfilling` | durable work is catching up | observe backlog and oldest age |
| `degraded` | dependency/config failure or terminal jobs | repair cause, then redrive |
| `disabled` | core works without configured semantic search | configure RAG if required |

From VM100, use commands that do not print `.env`, `vaults.json`, note bodies,
or job payloads:

```bash
cd /opt/apps/couchloom/releases/8f7a8e0
COUCHLOOM_IMAGE_TAG=8f7a8e0 docker compose \
  -f deploy/vm100/compose.yml \
  --env-file /opt/apps/couchloom/run/.env ps

docker exec couchloom bun -e \
  "const r=await fetch('http://127.0.0.1:8787/ready'); console.log(r.status, await r.text())"

docker exec couchloom bun -e \
  "const r=await fetch('http://127.0.0.1:8787/metrics'); console.log(await r.text())"

docker stats --no-stream couchloom couchloom-postgres couchloom-ollama
```

Initial alert thresholds:

- critical: failed queue jobs remain above zero for five minutes;
- warning: oldest queued/retrying job reaches 600 seconds for five minutes;
- warning: coverage stays below `0.999` for 15 minutes after a source change;
- warning: warm semantic-search p95 reaches 300 ms for 15 minutes;
- critical: the scheduled CouchDB or PostgreSQL backup is absent.

## Deployment and upgrade

The production release is an exact, immutable source tree, not a mutable
working checkout. Before a rollout:

1. Create a new `/opt/apps/couchloom/releases/<git-sha>` directory from the
   reviewed Git commit.
2. Back up the current source/config references and create a PostgreSQL custom
   dump with restrictive permissions.
3. Render and validate Compose using the production `.env`; do not print the
   rendered secrets into logs.
4. Build `couchloom:<git-sha>` and start the new release. Recreate only
   CouchLoom unless a dependency change explicitly requires more.
5. Verify container security settings, `/health`, `/ready`, metrics, queue
   state, coverage, MCP authentication, metadata read, semantic search, create,
   and edit. Confirm destructive tools remain absent.
6. Retain the previous image and release until the observation window passes.

Reference validation commands:

```bash
cd /opt/apps/couchloom/releases/<git-sha>
COUCHLOOM_IMAGE_TAG=<git-sha> docker compose \
  -f deploy/vm100/compose.yml \
  --env-file /opt/apps/couchloom/run/.env config --quiet

COUCHLOOM_IMAGE_TAG=<git-sha> docker compose \
  -f deploy/vm100/compose.yml \
  --env-file /opt/apps/couchloom/run/.env build --pull couchloom

COUCHLOOM_IMAGE_TAG=<git-sha> docker compose \
  -f deploy/vm100/compose.yml \
  --env-file /opt/apps/couchloom/run/.env up -d
```

Changing `EMBEDDING_DIMENSIONS` changes the pgvector column type and requires a
planned compatible restore or full derived-index rebuild. Do not treat it as a
normal rolling configuration change.

## Backup and restore boundary

A recoverable backup contains:

1. CouchDB under the Homelab CouchDB backup/replication policy;
2. a PostgreSQL 17 custom-format dump, including pg-boss queue state;
3. the mode-`0600` `.env` and vault configuration or their independently
   restorable secret source;
4. the source commit, Compose manifest, image digest, and model identity.

Current verified pre-rollout artifacts under `/opt/apps/couchloom/run` are:

- `src-backup-20261013-0318.tgz`;
- `env-backup-20261013-0318`;
- `vaults-backup-20261013-0318.json`;
- `postgres-backup-20261013-0318.dump`.

All are mode `0600`; the custom dump passed `pg_restore --list`. A backup is
not considered complete until it restores into an isolated PostgreSQL 17
instance and is verified against a non-production CouchDB copy. Never run a
restore drill against production CouchDB with write tools enabled.

## Failure runbooks

### Ollama or embedding model unavailable

1. Confirm `/ready` still reports the core service available and that metadata
   tools work.
2. Inspect `docker logs --tail 200 couchloom-ollama` and verify the model with
   `docker exec couchloom-ollama ollama list`.
3. Restart only Ollama if required.
4. Watch backlog and oldest-job age fall. Redrive dead-letter work only after
   the model endpoint is healthy.

### PostgreSQL unavailable

1. Treat this as a durable-work outage; the CouchDB checkpoint will not advance
   past changes that cannot be enqueued.
2. Restore the existing PostgreSQL volume/service without reinitializing it.
3. Restart CouchLoom after PostgreSQL is healthy to recreate pg-boss and
   pgvector connection pools.
4. Verify checkpoint progress, coverage 1, backlog 0, and failed 0.

### CouchDB or changes feed unavailable

1. Verify `couchdb` DNS and connectivity over `homelab-net` and inspect
   CouchLoom logs.
2. Restore connectivity. The feed resumes from the last acknowledged
   checkpoint; duplicate delivery is idempotent.
3. Confirm the checkpoint advances and reconciliation restores full coverage.

### Terminal queue failures

Fix the dependency or configuration problem first. Then use the redrive command
from the CouchLoom source runbook `docs/RAG_OPERATIONS.md`. Never delete or edit
pg-boss tables by hand, and do not repeatedly redrive a recurring failure.

## Rollback

The retained pre-hardening image is
`sha256:e2aeb316cb3d73b3e125a1402fc031c67dce0998d3154e12985a1356ec79605d`
(`couchloom:vm100-20261005-direct-couchdb`). The validated hardened image is
`sha256:cdca747d4df568004cfb02ec7477a3e77d8c33d11333693d0468c9a9b5307085`.

To roll back, capture the failed container status/logs, select the retained
release and tag, validate Compose, and recreate only CouchLoom. Do not delete
PostgreSQL to clear a queue and do not downgrade its data directory across a
PostgreSQL major version. After rollback, verify `/ready`, per-vault index
status, metadata, semantic search, backlog, failures, and the MCP tool catalog.

## Production evidence

- Controlled Ollama outage: metadata remained available, backlog became 1,
  failed remained 0, and the service returned to ready 23 seconds after Ollama
  restarted. The test note was restored exactly.
- Retry drill: the retry counter increased for recoverable failed attempts and
  the final queue returned to coverage 1, backlog 0, failed 0. The cumulative
  counter was 4 when production was rechecked on 2026-10-13.
- Ten warm semantic searches: p50 102.3 ms, p95 122.9 ms.
- Post-drill memory sample: CouchLoom 120.8 MiB of 2 GiB, PostgreSQL 91.96 MiB,
  Ollama 316.6 MiB.
- The authenticated smoke covered vault listing, metadata read, semantic
  search, create, and edit without recording note contents.

## Automation roadmap

The runtime is hardened, but deployment and recovery still require too much
operator SSH. The next infrastructure phase should encode the existing runbook,
without changing its safety gates:

1. Ansible role for immutable release upload, mode-`0600` config placement,
   Compose validation, image build, and targeted replacement.
2. Automated preflight/backup gate that refuses deployment when the database
   dump or config snapshot cannot be verified.
3. Post-deploy health gate for security settings, ready state, queue drain,
   coverage, MCP smoke, and rollback on core failure.
4. Prometheus scrape and alerts for coverage, queue age, retries, failures, and
   service availability.
5. Scheduled isolated restore drill with a report stored outside VM100.
6. Semaphore or an equivalent audited UI/API as the controlled execution layer;
   direct SSH remains break-glass access, not the normal workflow.

This roadmap is **not deployed yet**. Automation must consume secrets from the
approved private store and must never emit them or note content into job logs.

## Agent-readable facts

```yaml
service: couchloom
status: healthy
role: markdown_second_brain_mcp_and_local_semantic_index
host: vm100-prod
host_ip: 10.10.0.31
runtime: docker_compose
release_commit: 8f7a8e0
merged_main_commit: f5e322c
release_path: /opt/apps/couchloom/releases/8f7a8e0
mcp_endpoint: http://couchloom:8787/mcp
public_ports: []
networks:
  - couchloom-internal
  - homelab-net
source_of_truth: couchdb_livesync
queue_and_vector_store: couchloom-postgres
embedding_runtime: couchloom-ollama
embedding_model: nomic-embed-text
embedding_dimensions: 768
external_embedding_provider: false
documents_expected: 1357
documents_indexed: 1357
chunks: 6074
coverage: 1
backlog: 0
failed: 0
retries_total_observed: 4
write_policy: authenticated_create_and_edit_all_vault_paths
destructive_mcp_tools_exposed: false
normal_deployment_automation: pending
direct_ssh_role: current_operator_path_then_break_glass
```

## Source references

The implementation-level documents live in the CouchLoom repository:

- `docs/VM100_RUNBOOK.md` — deployment topology and production rollout;
- `docs/RAG_OPERATIONS.md` — queue inspection, redrive, metrics, rebuild, and
  failure recovery;
- `docs/RAG_ARCHITECTURE.md` — semantic indexing design;
- `deploy/vm100/compose.yml` — secret-free runtime manifest;
- `llms.txt` — agent-readable project index.
