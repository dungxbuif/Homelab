# Knowledge Hub Watchlists & Discovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Monitor saved resources, explain meaningful changes and improve source
selection from explicit feedback and bounded new-source discovery.

**Architecture:** One n8n dispatcher selects due targets from canonical Markdown
watch settings reconciled to operational state. Changes feed the same Core
analysis/writer and Daily reports; feedback/discovery reuse shared state/budget.

**Tech Stack:** Existing n8n HTTP/API/Data Table/AI/channel nodes, GitHub read
APIs/conditional fetch, Core/Daily contracts and Node built-in tests.

**Spec:** [Approved design](../specs/2026-10-14-news-intelligence-design.md).
**Master:** [Mandatory constraints](2026-10-14-news-intelligence.md).
**Prerequisites:** [Core](2026-10-14-knowledge-hub-core.md) and
[Daily](2026-10-14-knowledge-hub-daily.md).

## Global Constraints

All master rules apply: <=20 active watches, repo releases every 6h and
repo docs/commits/articles every 24h; hourly dispatcher, Sunday 08:00 synthesis.
Discovery Sunday 10:00 <=5 trials/week for 7 days. Hot alerts >=90 with primary/
corroboration <=3/day, quiet 22:00–07:00. Shared 30 calls/day automatic max 20;
unchanged checks consume no LLM. No autonomous code/tool/credential/budget edits.

## Review Focus

- Failed persistence cannot advance processed baseline (Task 1).
- 304/noise/no releases/inaccessibility is not an invented change (Task 1).
- Duplicate/unauthorized feedback cannot corrupt preferences (Task 2).
- Discovery cannot register private/local endpoints as public feeds (Task 3).
- Digest/alert duplication and quiet-hour boundaries obey caps/local dates (Task 3).

## Files and Interfaces

Feature-relative: watch/change/feedback schemas, `lib/{watch,feedback}.cjs`,
watch/feedback/discovery tests and fixtures, change/discovery prompts,
watch/change templates, `workflows/{watch,feedback,discovery}.json`.
Extend Daily reports and Core channel routing through existing nodes.

`Watch`: resource/type/target, enabled/status/interval, last observed/processed
versions, saved/delivered refs and next due. `Change`: change/resource IDs,
old/new version evidence, changed sections/files, URLs and stage states.
`dueWatches(watches,now) -> Watch[]`;
`detectChange(previous,fetched) -> Change|Unchanged|FetchFailure`;
`applyFeedback(preferences,event) -> UpdatedPreferences`;
`evaluateSource(candidate,sample,history) -> {status,reasons}`.

### Task 1: Canonical Watchlists and Durable Change Analysis

**Files:** watch/change schemas/helpers/templates/tests and watch export.
**Consumes:** Core resource/intake/writer and Daily watched-resource section.

- [ ] Test pause/overflow, repo without releases, bare tag vs release, rewritten
  branch, rename/redirect, 304/404/429, noisy page, save failure and replay.
  Run watch tests and confirm failures before implementation.
- [ ] Create canonical `tracking/watchlists/` entries for submitted fetchable
  resources by default; honor `watch:false`/pause. Ordinary chat URL is not
  a watch. Beyond 20 targets show `pending_capacity` without losing capture.
- [ ] Reconcile Markdown before scheduling; hourly dispatcher evaluates next due,
  not one cron per resource. Use provider IDs/SHA/tag, ETag/Last-Modified and
  normalized hashes with rate-limit/deadline handling.
- [ ] Save old/new evidence and sourced `staging/updates/` change before advancing
  processed baseline. Keep observed/processed/saved/delivered cursors separate;
  unchanged checks make zero model calls and temporary failures retain baseline.
- [ ] Add daily/weekly change synthesis tied to related notes/projects. Suggest
  impact/actions without deploying software or changing project dependencies.
- [ ] Replay a two-version fixture across save failure/restart: one saved change,
  retained evidence, retried original baseline and skipped paused targets.
  Run tests and commit the independently usable watch slice.

### Task 2: Explicit Feedback and Bounded Personalization

**Files:** feedback schema/helper/tests/fixtures/export; common channel routing.

- [ ] Test duplicate update, unknown resource/report, unauthorized chat/actor,
  conflicting feedback, stale entity and cross-platform numeric-ID collision.
- [ ] Route `useful|skip|follow` from both channels with shared entity IDs; clicks
  are not reading/approval and never mark study/tasks complete.
- [ ] Implement weights clamped 0–2, initial 1 and explicit +/-0.1 change.
  Preserve >=3 active sources/topic when reducing coverage and retain history.
- [ ] Run tests/replay identical feedback twice: one weight change, no identity
  leak, shared preferences only for explicitly mapped users. Commit this task.

### Task 3: Source Trials, Alert Limits and Full Acceptance

**Files:** discovery prompt/export/tests/fixtures; extend collect/watch/deliver,
schemas and human/agent docs.

- [ ] Test dead/stale/duplicate feeds, private/local URLs and private redirect,
  insufficient recent evidence, trial cap/week boundary, low budget, duplicate
  event and quiet-hours boundary. Run discovery tests before implementation.
- [ ] Discover from topic search and useful source/repo references; validate
  fetchability/recency/topic/identity. Admit <=5 trials/week for 7 days; promote
  >=3 relevant unique items with no repeated fetch failures, otherwise pause
  after trial. Keep history and existing coverage when discovery fails.
- [ ] Alert only evidence-backed score >=90, <=3/day; share event dedup with
  digest and queue quiet-hour events for morning. Share Core call/token budgets;
  no autonomous agent/tool/credential/infra expansion.
- [ ] Shadow trials/alerts 7 days before live adoption/notifications; prepare
  concrete activation/rollback evidence for the existing operator gate.
- [ ] After authorized activation, verify capture -> durable analysis -> ideas
  after memory expiry -> version change -> dual-channel report -> feedback ->
  validated trial, plus outages/restart/caps/retention and independent receipts.
- [ ] Reconcile human runbook/JSON schemas, deployment record, catalog/navigation/
  `llms.txt`; run tests/links, record backup/rollback and commit only feature files.
