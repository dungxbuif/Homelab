# Knowledge Hub Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Capture notes/articles/repos, save sourced classified Markdown, and
support interactive Mezon/Telegram Q&A and future idea retrieval.

**Architecture:** Existing channel nodes and Obsidian Inbox feed n8n. Save human
input before AI work; a read-tool AI Agent returns structured analysis and a
validated deterministic writer persists it through CouchLoom.

**Tech Stack:** Existing n8n/MCP/Data Tables/AI/channel nodes, CouchLoom/LiveSync,
Node built-in tests; no required new service or SDK.

**Spec:** [Approved design](../specs/2026-10-14-news-intelligence-design.md).
**Master:** [Mandatory constraints and budgets](2026-10-14-news-intelligence.md).

## Global Constraints

All master constraints apply. Core: max 64 KiB UTF-8 capture, 100 pending items,
30 model calls/day including retries, automatic max 20; description 2–4 sentences,
retained knowledge no expiry, ordinary chat separate, both channels as n8n nodes.
No production activation or new SDK/gateway project is part of local implementation.

## Review Focus

- Concurrent retries preserve originals/revisions and readback (Tasks 1–2).
- UTF-8 limits count bytes, not JavaScript character count (Task 2).
- Fetched instructions/invented citations cannot become saved claims (Task 3).
- Numeric sender ID collision across platforms cannot share private memory (Task 4).
- Failed/unknown delivery cannot resend a successful channel (Task 5).

## Shared Files and Interfaces

All feature paths below are relative to `automation/knowledge-hub/`.
Create `config/{runtime-capabilities,topics}.json`, `schemas/*.schema.json`,
`lib/*.cjs`, `prompts/*.md`, `templates/*.md`, `tests/*.test.cjs`, synthetic
`fixtures/`, generator and inactive `workflows/*.json`.

- `Intake`: intake ID, origin/actor/vault, original path/text, submitted URL,
  content hash, capture time, intent (`capture|analyze|watch`), status.
  Intake status: `queued|saved|pending_analysis|analyzed|failed`.
- `Resource`: resource ID, kind (`note|article|analysis|github_repo`), canonical
  URL/repo identity, origin/sources, observed version and dossier path.
- `KnowledgeRecord`: ID/resource/type/title/description/tags/topics, related
  projects/paths, sources, capture/analysis/verification dates, optional SHA/tag/
  hash, status, supported claims, interpretation, applications, limits/questions.
- `RenderedNote`: `{path, markdown, content_hash}`. Writer result:
  `{state: saved|reused|revision|pending|failed, path, hash, deep_link}`.
- `Reply`: originating platform/conversation/thread, parent event, text,
  evidence/note links and optional job/attachment refs.
- `Report`: ID/date/kind/topic, resource/story IDs, sourced claims, interpretation,
  related paths, coverage and `ai|link_roundup|partial` state.

### Task 1: Confirm Runtime and Generate Inactive Workflow Contracts

**Files:** runtime/topics config, `scripts/generate-workflows.cjs`,
`tests/workflow.test.cjs`, README; `docs/deployments/knowledge-hub.md`.
**Produces:** actual node versions/credentials references/vault/model/search,
budgets/deadline, ingress ownership and serialization evidence.

- [ ] Read approved spec/runbooks; inspect deployed AI Agent, Data Tables, MCP
  Client/Tool, Mezon/Telegram receive/reply and error nodes via supported UI/API.
- [ ] Verify private MCP auth/list/read/search; write/readback only a designated
  test note. Confirm actual transport fields and absent delete/move/rename.
- [ ] Test overlapping manual executions for reliable writer/budget serialization.
  If unavailable, record durable lock/queue prerequisite and keep affected
  pilot inactive/manual; static flags are not an atomic lock.
- [ ] Record authorized credential references, tool-capable model/search,
  input/output token/cost/deadline limits and Mac/model-offline behavior.
- [ ] Record Data Table storage capacity and supported node operations; ensure
  bounded queue/chat retention fits. Insufficient storage must produce an
  explicit failed/queued response, never an acknowledgment of lost input.
- [ ] Confirm one ingress owner per bot; probe node receipt/reply/restart only
  now, without stealing a webhook/listener or creating a new SDK design.
- [ ] Write `rejectsActiveExport`, `rejectsInlineSecret`,
  `rejectsUnrecordedNodeVersion`; run
  `rtk proxy node --test automation/knowledge-hub/tests/workflow.test.cjs`.
  Confirm failures before implementing the generator.
- [ ] Implement inactive exports using recorded node types/versions and credential
  references; rerun until valid fixtures pass and invalid exports are rejected.
- [ ] Record evidence/rollback in deployment note and commit only task files.

### Task 2: Durable Capture, Inbox Detection and Scoped Persistence

**Files:** intake/knowledge schemas, `lib/{intake,policy}.cjs`, matching tests,
capture template and `workflows/{intake,vault-intake,persist}.json`.
**Interfaces:** `normalizeIntake(event) -> Intake`;
`validateWrite(vaultId,path,markdown,allowedVaultId) -> ApprovedWrite|Rejection`.

- [ ] Write tests: duplicate event, changed user text, UTF-8 >65536 bytes, queue
  item 101, path traversal/wrong vault, lost readback, MCP outage and concurrent
  attempts. Run intake/policy tests; confirm expected failures before helpers.
- [ ] Implement explicit save/designated Inbox/standalone resource capture.
  Ordinary chat and URLs inside questions are context, not automatic save/watch.
- [ ] Persist pending input through `hub_intake` nodes/API before acknowledgment.
  `queued` requires durable queue; `saved` requires vault readback. Reject
  overflow explicitly; clear temporary text only after vault persistence.
- [ ] Poll Inbox/`ai-process` every 15 minutes. Actual `list_notes` has
  modified-after/limit but no offset: overlap windows, hash-dedupe, detect
  truncation and reconcile totals before advancing watermark. Exclude AI output.
- [ ] Validate writer prefix/vault; read target/hash, create/reuse or write a
  linked revision draft. Do not claim read-before-write is atomic; demonstrate
  human-edit/retry interleavings retain originals before any automatic replacement.
- [ ] Run tests and manual capture while LLM is down plus offline-phone sync.
  Expect one preserved original and correct queued/saved/pending-analysis state.
- [ ] Document capture/replay/backup and commit this independently usable slice.

### Task 3: Sourced Analysis, Metadata, Classification and Durable Notes

**Files:** resource/render/organize helpers/tests, resource/knowledge schemas,
article/repository/organize prompts, dossier templates and analysis/organize workflows.
**Interfaces:** `identifyResource(input) -> Resource`;
`validateKnowledge(record,evidence) -> ValidRecord|Errors`;
`renderKnowledge(record) -> RenderedNote`;
`classifyResource(resource,topics,projects) -> Classification`.
`Classification`: primary topic, secondary tags, related project/note paths,
confidence and reasons; uncertainty is provisional.
`buildDossier(topic,resources,relationships) -> KnowledgeRecord`, with sourced
`about|supports|contradicts|updates|related_project` relationships.

- [ ] Test unavailable article, repo without releases, unknown author/date/license,
  unsupported version claim, invented URL, injected instructions, conflicting
  claims, new resource version, generic description and human-edited dossier.
  Run tests and confirm failures before implementation.
- [ ] Implement stable identity and source analysis plus <=5 selected vault notes.
  Fetch additional evidence only for a gap/verification or explicit deepening.
  Read selected GitHub metadata/README/docs/files; never run/install the repo.
- [ ] Allowlist only controlled search/fetch and MCP read/list/search tools for
  the AI Agent. Keep write/edit tools and arbitrary HTTP/exec outside the agent;
  structured results reach the validated writer, not model-selected raw endpoints.
- [ ] Reserve/check calls/tokens/cost before model work; count retries, protect
  the explicit-request reserve and keep input saved when analysis queues.
- [ ] Validate substantive 2–4-sentence description, tags/topics/provenance,
  supported claims and known dates/SHA/tag. Unknown facts stay unknown.
- [ ] Render workings, applications, limits/questions at appropriate depth.
  Link topics/projects without moving/copying originals; persist with Task 2's
  readback/revision policy and return the actual saved note link.
- [ ] Replay one note/article/repo twice and after restart. Expect retained source,
  classified durable knowledge and correct links. Run tests and commit this slice.

### Task 4: Interactive Chat and Future Idea Retrieval

**Files:** reply schema, research prompt, query/chat workflows,
chat fixtures and workflow/organize tests; use existing channel nodes.
**Consumes:** Core resource/knowledge/writer. **Produces:** scoped Reply/job.

- [ ] Test both channels with Q&A -> follow-up -> save -> watch intent -> status;
  include duplicate/self messages, unauthorized group, numeric ID collision,
  wrong thread and no evidence. Assert ordinary chat saves zero permanent notes.
- [ ] Configure history namespace by platform/tenant/chat/thread/user mapping,
  30-day proposed retention and <=20 recent messages within token cap; no
  inferred cross-platform identity linking.
- [ ] Route natural follow-ups/save/deepening to common workflows and reply to
  origin. Long jobs have durable job/status/completion; queued watch intents stay
  visibly pending until the Watch slice is active.
- [ ] Query metadata/search then selected canonical notes; cite note/source links,
  distinguish stored facts/new suggestions, stale evidence and contradictory drafts.
- [ ] Clear test chat memory and ask for project ideas from retained resources.
  Assert actual saved-note references still appear; weak/no matches report gaps.
- [ ] Run fixtures/manual chats, phone/desktop reading and restart recovery;
  commit this independently usable end-to-end slice.

### Task 5: Per-Destination Delivery, Recovery and Core Acceptance

**Files:** deliver/error workflows, delivery tests/fixtures, generator exports;
human runbook and `docs/services/knowledge-hub.schema.json`.
**Interfaces:** `deliveryKey(reportId,destination) -> string`; receipt state
`pending|delivered|failed|unknown`, independent of note persistence.

- [ ] Test 429/rejection, accepted message with lost response, one channel failing
  after the other succeeds, duplicate retry, unsaved note and offline model.
- [ ] Implement short report plus `.md` where supported and note/report link
  fallback. Retry failed destinations only; uncertain acceptance is `unknown`
  for reconciliation. Interactive replies do not broadcast by default.
- [ ] Export affected settings, prepare inactive imports and concrete activation/
  rollback evidence. Obtain the separate homelab operator gate before production
  mutation or recurring messages; do not restart existing services casually.
- [ ] After authorized activation, test capture -> analyze -> readback -> desktop/
  phone read -> follow-up -> ideas after memory expiry -> replay/outage/restart.
- [ ] Reconcile human/agent docs and actual catalog/navigation, record backup/
  rollback, run tests/links and commit only Core artifacts. Preserve gold/fuel.
