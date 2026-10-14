# Knowledge Hub Daily Research Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Collect multi-topic news, research selected stories and deliver saved
Vietnamese daily Markdown through the configured Mezon/Telegram destinations.

**Architecture:** Add sources/normalization/event grouping/schedules to Core's
analysis, budget, writer and receipts. No second knowledge store or LLM owner.

**Tech Stack:** Existing n8n RSS/HTTP/Data Table/AI nodes, Core workflows,
Node built-in tests. Horizon remains optional after the native slice works.

**Spec:** [Approved design](../specs/2026-10-14-news-intelligence-design.md).
**Master:** [Mandatory constraints](2026-10-14-news-intelligence.md).
**Prerequisite:** [Core Tasks 1–5](2026-10-14-knowledge-hub-core.md).

## Global Constraints

All master rules apply: <=20 seed sources, hourly <=100 items/run, 07:00 local
digest <=10 stories/3 deep dives, shared 30 model calls/day automatic max 20,
20-second fetch/max 3 attempts/5–30-second retry, source gaps visible,
persist/readback before notify, no silent fallback or whole-web coverage claim.

## Review Focus

- Syndication groups one event, distinct repo releases remain separate (Task 1).
- Missing dates are not guessed from discovery time (Task 1).
- Failed feed remains a named coverage gap (Tasks 1–2).
- Same-day retry cannot overwrite human edits or resend acknowledgments (Task 2).
- Offline model/budget cap produces honestly labeled degraded output (Task 3).

## Files and Interfaces

Feature-relative files: item/report schemas, `lib/{normalize,select}.cjs`,
matching normalize/select/daily tests, source fixtures, daily prompt/digest
Markdown template, `workflows/{collect,digest}.json`.

`Item`: story/source IDs, URL/canonical URL, title, nullable publication time,
observed time, topic, event key, evidence URLs and processing state.
`normalizeItem(input,source,observedAt) -> Item|RejectedItem`;
`selectItems(items,preferences,limits) -> {selected,rejected,coverage}`.
Reuse Core Resource/KnowledgeRecord/Report/writer/receipts. Daily report ID:
`daily:<local-date>:v1`.

### Task 1: Bounded Multi-Source Collection and Event Selection

**Files:** item schema, normalize/select helpers/tests, fixtures, collect export.
**Produces:** replayable selected items and coverage for Core analysis.

- [ ] Test tracking URLs, syndication, distinct repo releases, missing/invalid
  dates, stale items, failed peer feed and 100-item cap. Run normalize/select
  tests with `rtk proxy node --test`; confirm failures before helpers.
- [ ] Implement identity/selection preserving observed vs published time and
  evidence URLs; group same-event reports, retain genuinely different versions.
- [ ] Seed <=20 official AI/blog/HN/GitHub/engineering feeds/APIs via supported
  Data Table nodes. Label star-gain discovery accurately; exact GitHub Trending
  needs a verified adapter. Social access is never assumed from a URL alone.
- [ ] Generate inactive RSS/HTTP fetch flow with bounded retries/rate-limit
  handling. Store metadata/markers, not source bodies, in operational tables.
- [ ] Replay fixtures twice and after restart: stable IDs, no duplicate selected
  event, distinct releases, explicit unavailable sources. Run tests and commit.

### Task 2: Sourced Daily Markdown Using Core Knowledge

**Files:** report schema, daily prompt/template, digest export and daily tests.
**Consumes:** selected items/coverage and Core budget/analysis/writer/receipts.

- [ ] Test unsupported source claim/URL, contradictions, superseded release,
  11th story/4th deep dive, human-edited report and write-success/receipt-failure.
- [ ] Analyze <=10 stories, deepen <=3 through Core's source+vault policy and
  <=5 relevant notes, with <=3 suggested actions. Reuse saved resource identity
  instead of duplicating dossiers or paying for identical analysis again.
- [ ] Render Vietnamese facts/why-it-matters/project relevance/source links/
  coverage at `staging/news/YYYY-MM-DD-digest.md`; use Core hash/revision/readback.
- [ ] Reconcile report/receipt state on retry; reuse unchanged output, create
  revisions for human-edited/changed output, persist before notifying.
- [ ] Run tests and manual fixture report; expect citations, enforced limits,
  correct links/retained edits and per-destination retry. Commit the daily slice.

### Task 3: Schedule, Degraded Output and Three-Day Acceptance

**Files:** collect/digest/error exports, daily tests/fixtures, runbook/schema.

- [ ] Test timezone midnight, model offline, exhausted budget, feed/MCP/provider
  outage and overlapping manual/scheduled runs; confirm missing behavior fails.
- [ ] Add hourly collection and 07:00 local digest using confirmed serialization
  and shared counters. Keep n8n the sole schedule owner for this workflow.
- [ ] On incomplete AI work, persist a clearly labeled link roundup or queue
  analysis, preserving source gaps. No stale output is called fresh research.
- [ ] Prepare schedule/import/rollback diff and activate only under the operator
  gate. Observe 3 daily runs, caps, phone/desktop read, retry/restart, unchanged
  gold/fuel report and explicit degraded behavior.
- [ ] Reconcile sources/provider/schedules in human/agent docs, run tests/links,
  record export/backup/rollback evidence and commit only this slice.
