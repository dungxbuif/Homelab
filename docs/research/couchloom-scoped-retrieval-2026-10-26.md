# CouchLoom scoped retrieval verification

## Change and deployment

Application commit `9541933`, deployed image
`sha256:a6ec26af86e8189a6eef092ace9578ba4461d1524eb89ff4485afcb18efe5c5c`.
Source is on CouchLoom branch `codex/rag-quality-eval`. No embedding/index rebuild,
source-note writes, credential changes, or gold-price workflow changes occurred.
Infrastructure remains the network anchor from homelab-ops `dc8b606`.

`search_notes` accepts an optional literal folder; it filters before top-K and
retains vault isolation. Omission preserves previous retrieval. Example:
`{"vault_id":"personal","query":"Redis leaderboard","folder":"wiki","limit":5}`.
Tool guidance requires reading the source and distinguishes similarity from
factual confidence. Broaden scope when the desired evidence is outside wiki.

## Evidence

The frozen 12-case set combines both earlier probes, covering only three notes.
The evaluator uses authenticated MCP initialize, tool discovery and tool calls;
it fails on RPC errors or scope violations. Source and reports are committed
under CouchLoom `tools/rag-eval.ts` and `eval/`.

| Mode | Known-note hit@5 | MRR@5 |
| --- | ---: | ---: |
| Before, unrestricted | 6/12 | 0.3403 |
| After, unrestricted | 6/12 | 0.3403 |
| After, explicit wiki scope | 9/12 | 0.6111 |

All returned paths are distinct. Wiki-scoped retrieval receives known source
location, so 9/12 is not a general accuracy score. The original Vietnamese Redis
question and revised English pool/blockchain questions still fail. Other valid
sources are not comprehensively labeled. Answer correctness, refusal behavior,
and live Mezon delivery were not assessed. No production-ready claim is made.

Validation: 188 unit tests, 3 real PostgreSQL integration tests and 31 local MCP
E2E tests passed; build succeeded. Production readiness returned HTTP 200,
coverage 1, backlog 0, failed 0. Five sampled stored embeddings matched fresh
embeddings with cosine approximately 1; this is not a full index audit.
Latency spikes reached 3.8 seconds after restart and 2.6 seconds in scoped tests.

## Capacity, backup and rollback

VM100 initially had 138 MB free. The existing approved Docker maintenance unit
ran successfully; free space rose to about 4.9 GB and was 4.5 GB after rollout.
Maintenance applies its existing age/retention policy; no manual volume pruning
or backup deletion was used. Capacity remains a blocker for a large rebuild.

Image built locally, then loaded into VM100. Pre-rollout PostgreSQL dump resides
on the operator workstation at
`/home/dungxbuif/.local/state/couchloom-backups/20261026-pre-9541933.dump`,
27,399,389 bytes, mode 0600 inside a mode-0700 directory.
`pg_restore --list` succeeded; a full restore drill has not been performed.

Rollback uses retained release/image `ae9d28c`: run its Compose base with the
existing `knowledge-hub.network.override.yml`, production env file, and
`COUCHLOOM_IMAGE_TAG=ae9d28c`; recreate only CouchLoom with `--no-deps`.
Keep `couchloom-network_anchor` running. No schema rollback is needed.

Next: resolve capacity, freeze an independently reviewed 40–60-case evaluation,
then test task-prefix/model/chunk changes in a separate index. Do not replace
the production model based on this small, source-biased set.
