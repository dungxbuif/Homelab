# CouchLoom retrieval baseline — 2026-10-26

## Scope and evidence

Initial inspection of VM100 and a small retrieval probe against its existing
PostgreSQL index, followed by a scoped CouchLoom retrieval rollout. No credential,
vault content, embedding, or raw database row was changed. This is not an
answer-quality certification.

At the start, `couchloom:knowledge-hub-513596e` was stopped (exit 255). The
Swarm manager still owned `homelab-net`, but VM100 had dropped its local overlay
metadata after losing the final running endpoint. PostgreSQL and Ollama remained
healthy. A temporary constrained Swarm anchor restored the overlay long enough
to recreate CouchLoom; the anchor was removed after the real endpoint attached.

Index: 1,365 documents in vault `personal`, 6,099 chunks, mean chunk length
1,539 characters, zero orphan chunks. Recorded model is `nomic-embed-text`;
loaded Ollama model ID is `0a109f422b47`. Latest document update is
2026-10-24 06:15:09 UTC. Coverage against the current vault is unverified.

## Probe

Three known notes were inspected in the stored index to establish relevance.
Six questions were embedded using Ollama and searched using pgvector cosine
distance, scoped to `personal`, returning five chunks. This bypasses the stopped
MCP service and does not reproduce any additional MCP filtering/ranking.

| Case | Question | Expected note | Rank, plain query | Rank, `search_query: ` |
| --- | --- | --- | --- | --- |
| vi-pool | Khi gọi Close, kết nối được đóng hẳn hay trả lại pool? | `wiki/engineering/database/connection-pools.md` | 1 | 1 |
| en-pool | Does closing a borrowed database connection return it to the pool? | same | 4 | absent |
| vi-redis | Lệnh nào lấy top 10 người đứng đầu bảng xếp hạng Redis kèm điểm? | `wiki/engineering/caching/redis.md` | absent | absent |
| en-redis | Which Redis command returns the top ten leaderboard members with scores? | same | absent | absent |
| vi-chain | Indexer blockchain có thông lượng backfill và độ trễ commit bao nhiêu theo ghi chú? | `wiki/concepts/blockchain.md` | absent | absent |
| en-chain | What backfill throughput and commit latency are recorded for the blockchain indexer? | same | 1 | 1 |

Known-note hit@5: 3/6 plain, 2/6 query-prefixed. These are not context recall
scores: other returned documents may also answer a question, and only one
relevant note per question was labeled. This small, selected sample is diagnostic,
not a representative benchmark. Prefix was changed only for queries; document
embedding prefix/model provenance remains to be verified.

Plain-query embedding plus SQL subprocess latency ranged 0.423–2.130 seconds;
prefixed queries 0.296–0.971 seconds. Cache/warmup/order were uncontrolled, so
these timings do not prove one approach faster. No generation or delivery was timed.

Both Redis questions missed the known command-bearing note. Several top-five
lists contained repeated paths; the English Redis probe returned four chunks
from `projects/99tech-challange/problem6/README.md`.

## Next evaluation and improvement order

1. Restore the declared CouchLoom network topology through the operational
   repository, then verify MCP readiness and index freshness.
2. Freeze a 40–60-question Vietnamese/English dataset with evidence passages,
   alternate valid sources, exact identifiers, multi-note questions, outdated
   notes, and unanswerable questions. Keep tuning and held-out cases separate.
3. Compare current retrieval with lexical + vector fusion and per-document
   diversity. Respect vault scope and source status; prefer curated wiki evidence
   where appropriate without excluding relevant project notes.
4. Compare heading-aware chunks and a multilingual embedding candidate such as
   BGE-M3 in a separate index. Verify model-specific input conventions first.
5. Add reranking only if held-out accuracy improves enough to justify CPU/latency.
6. Measure known-evidence recall, nDCG, citation correctness, supported claims,
   abstention, p50/p95 latency, tokens, and resource usage. Human-review a sample;
   LLM judges alone do not establish correctness.

Keep Markdown/CouchDB and CouchLoom's access boundary. There is no measured
evidence yet that replacing the whole platform improves this vault's RAG.

## Remediation and production recheck

Deployed CouchLoom commit `ae9d28c` from immutable release
`/opt/apps/couchloom/releases/ae9d28c`, image digest
`sha256:048bf5d519e4791f08ecfe082a2f3ae00ca21f73764676114a144cc86f1494cc`.
The change selects only the best chunk per `(vault_id, path)` before applying
the result limit. Commit `ae9d28c` also replaces a production-incompatible
`ANY(array)` binding with a value-list binding; the pre-fix runtime smoke had
failed with PostgreSQL error `42809`.

Verification: 187 unit tests and the build passed from the exact deploy commit;
the pgvector integration suite passed 2/2. Production is healthy with readiness
HTTP 200, coverage 1, backlog 0, failed 0, 1,365 documents, and 6,099 chunks.
n8n reaches `/health` over `knowledge-hub-net`; unauthenticated MCP initialize is
rejected with HTTP 401. A PostgreSQL custom dump was verified with
`pg_restore --list` before rollout and retained at
`/opt/apps/couchloom/run/postgres-backup-20261026-pre-c32d5af.dump`.

The post-deploy six-case probe used revised questions, so it must not be compared
numerically with the original table. It returned five distinct paths for every
query and found the known Redis note at ranks 1 and 2; known-note hit@5 was 2/6.
Latency was 198–1,164 ms including local embedding. This proves diversity and
runtime correctness, not sufficient relevance quality.

Rejected experiment: unindexed full-text/RRF took about 3.2–4.4 seconds and did
not improve hit@5. Nomic document/query task prefixes remain a valid candidate,
but a read-only full-index trial was stopped after throughput projected above two
hours at the current 2-CPU Ollama limit. No prefix code or mixed-vector index was
deployed. The next gate is a frozen 40–60-question dataset and a separate index.

The recurring overlay failure is now controlled by the source-backed Swarm
stack `automation/stacks/couchloom-network-anchor/stack.yml` at `homelab-ops`
commit `dc8b606`. Its pinned Alpine task holds `homelab-net` on `vm100-prod`
without ports, data, or credentials. A forced CouchLoom recreate succeeded
without a temporary service, then readiness and semantic search passed again.
Migrating CouchLoom itself to Swarm remains optional, not a recovery blocker.

## References

- [pgvector hybrid search](https://github.com/pgvector/pgvector#hybrid-search)
- [Nomic task prefixes](https://huggingface.co/nomic-ai/nomic-embed-text-v1.5)
- [BGE-M3 model card](https://huggingface.co/BAAI/bge-m3)
- [Ragas metrics](https://docs.ragas.io/en/latest/concepts/metrics/available_metrics/)
