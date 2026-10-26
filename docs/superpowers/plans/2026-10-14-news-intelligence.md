# Personal Research & Knowledge Hub Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build one personal Markdown hub for automatic Inbox processing,
interactive Mezon/Telegram chat, daily research and recurring resource updates.

**Architecture:** Obsidian is the primary editor/reader, CouchLoom the private
vault interface, and n8n owns AI Agent execution, state, validation, schedules
and delivery. Mezon/Telegram are existing n8n nodes; resolve implementation
when needed, without a separate SDK/gateway design project.

**Tech Stack:** Existing n8n AI/MCP/Data Table/HTTP/RSS/channel nodes,
CouchLoom/CouchDB/LiveSync, selected LLM/search credentials, Node built-in tests.

**Spec:** [Approved design](../specs/2026-10-14-news-intelligence-design.md).
The user approved revision 4 on 2026-10-14; original design content commit
`709824d`. Execution ordering below refines sequencing without adding scope.

**Status:** Ready for implementation-plan review. Execution method is not
selected. No code, workflow imports/publication, credentials, live schedules,
recurring messages, deployments or production restarts changed during planning.

## Global Constraints

- Canonical repository: `/Users/dungxbuif/workspace/vaults/homelab`; feature root
  `automation/knowledge-hub/`. Preserve unrelated staged/dirty changes.
- Obsidian-first; automatic `raw/captures/` Inbox plus `ai-process` opt-in
  elsewhere. Both Mezon and Telegram support interactive chat through n8n nodes.
- Source + vault research first; external evidence for gaps/verification.
  Ordinary chat is not a permanent note; explicit captures preserve original text.
- Markdown/frontmatter is canonical; saved knowledge has no automatic expiry.
- Writer prefixes: `raw/news/`, `raw/captures/`, `raw/resources/`, `staging/news/`,
  `staging/notes/`, `staging/resources/`, `staging/topics/`, `staging/updates/`,
  `tracking/watchlists/`. Every MCP call uses the selected `vault_id`.
- Human originals are create-only via capture; AI output is separate. Preserve
  edits with revision drafts. No final wiki/governance/generated-index writes,
  nor move/rename/delete capability.
- Names/tags English, prose Vietnamese, relative links/wikilinks. Completed
  analysis requires substantive 2–4-sentence description, tags/topics, evidence,
  verification/version dates and saved/readback Markdown with a returned link.
- Capture max 64 KiB UTF-8; pending queue max 100. Save without waiting for AI.
- Model calls max 30/day including retries, automatic max 20 reserving 10 for
  explicit requests. Record/enforce token/cost caps and execution deadline
  before scheduled activation. No silent model/provider fallback.
- Collection hourly, <=100 items/run, <=20 seed sources. Daily report 07:00,
  <=10 stories and <=3 deep dives; timezone `Asia/Ho_Chi_Minh`.
- <=20 active watches; repo releases every 6h, docs/commits/articles every 24h;
  opted-in note scan every 15 minutes; weekly synthesis Sunday 08:00.
- Discovery Sunday 10:00, <=5 trial sources/week, 7-day trial.
- Hot alerts >=90/100 with primary/corroboration, <=3/day, quiet 22:00–07:00.
- Operational markers/chat memory 30 days; prompt max 20 recent messages within
  token cap. Retain watch baselines/identity for watch lifetime, saved knowledge
  indefinitely, unsaved intake until persisted; no silent history deletion.
- Fetch timeout 20 seconds; max 3 attempts with 5/30-second backoff, respecting
  rate limits within execution deadline.
- Serialize mutation/budget state before automatic activation. Data Table
  lookup/upsert/static data is not an atomic lock. Ambiguous channel acceptance
  is `unknown`, not automatic resend; do not claim exactly-once delivery.
- VM100 application compute, Pi5 datastore/edge; no new host/router ports,
  arbitrary agent SSH/Docker access, raw service-DB mutations or logged secrets.
- Preserve existing gold/fuel reporting. Production imports/restarts/activation
  follow the operator gate in homelab `index.md`; design/plan approval alone is
  not blanket production authorization.

## Review Focus

1. Concurrent/replayed writes retain human text and validate readback (Core 1–2).
2. Ambiguous provider receipt retries only the failed destination (Core 5).
3. Context/provenance mistakes cannot leak sessions or invent evidence (Core 3–4).
4. Source/model/budget failure saves first and reports pending/partial (Core/Daily).
5. Watch save failure cannot advance processed baseline and lose updates (Watch 1).

## Implementation Slices

| Order | Plan | Independently usable outcome |
|---|---|---|
| A | [Core: capture, analysis, chat and retrieval](2026-10-14-knowledge-hub-core.md) | Save a described/tagged/classified note and ask about it later from either chat |
| B | [Daily research and reporting](2026-10-14-knowledge-hub-daily.md) | Multi-topic daily Markdown, mobile delivery and coverage reporting |
| C | [Watchlists, feedback and discovery](2026-10-14-knowledge-hub-watch.md) | Meaningful update analysis, source trials and bounded personalization |

A is first because B/C reuse its writer, budget, resource identity and delivery
contracts. Native/inline execution is recommended: shared contracts and real
n8n integration behavior matter more than parallel coding here. Delegation is
available if the user selects it; no execution method is assumed approved.

## Artifact and State Boundaries

Feature paths: `config/`, `schemas/`, `lib/`, `prompts/`, `templates/`,
`fixtures/`, `tests/`, `scripts/generate-workflows.cjs`, `workflows/`.
Generate importable **inactive** exports using recorded deployed node versions;
credentials are references, never values. Fixtures contain synthetic data only.
The generator embeds tested pure helper logic in Code-node source where needed;
do not assume n8n can `require()` local feature modules or access Data Tables
directly from Code nodes. Use dedicated Data Table nodes/API for state and
record any required runtime builtin availability during preflight.

`config/runtime-capabilities.json` records non-secret node versions, credential
references, selected vault/model/search, budgets/deadline, serialization evidence
and bot ingress ownership. Missing inputs remain named preflight prerequisites,
not guessed credentials or authorization for upgrades.

Data Tables through supported nodes/API: `hub_intake`, `hub_resources`,
`hub_watches`, `hub_changes`, `hub_conversations`, `hub_messages`, `news_sources`,
`news_items`, `news_reports`, `news_feedback`, `news_preferences`. Original text
is temporarily queued only until vault readback. Conversation bodies are a
bounded operational exception; canonical knowledge/watch settings stay Markdown.

If deployed nodes cannot connect to the actual MCP transport or serialize the
new writer/budget flow, keep the affected pilot manual/inactive until that
specific prerequisite is resolved. Mezon/Telegram have no separate architecture
approval: verify and implement the existing nodes when their tasks need them.

## Documentation and Acceptance

Human runbook: `docs/services/knowledge-hub.md`; adjacent agent-readable
`knowledge-hub.schema.json`; deployment evidence:
`docs/deployments/knowledge-hub.md`. Update `docs/INDEX.md`, `docs/STACK.md`,
`docs/LOG.md`, `index.md`, `llms.txt` only with actual deployed facts.
RelayHub public docs do not change: no RelayHub product behavior changes.

Acceptance: article/repo capture in both chats -> retained original -> sourced
analysis with description/tags/topics -> phone/desktop read -> follow-up and
idea query after chat memory expires -> monitored change -> per-destination
report -> feedback -> validated source trial. Exercise retries, human edits,
model/feed/MCP/delivery outages, budgets, no duplicate accepted sends, three
daily runs and seven shadow-trial days. Every slice records rollback/backup.

## Optional Later Work

Horizon may replace collection only after verified stdio/HTTP integration,
authentication/timeouts and one owner for source state/scoring/LLM cost.
OpenClaw/OpenWorker are optional clients. Authenticated web capture/editor/report
views are separate optional enhancements; no whole-vault public exposure.

## Handoff

Review this master and Core slice, then select Native/inline or subagent-driven
execution. Design approval is recorded; this finalized plan and future
production activation remain their own review stages.
