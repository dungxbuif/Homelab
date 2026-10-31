---
type: Project
title: n8n-nodes-mezon
description: n8n community nodes for Mezon; installed in the running n8n
generated:
  by: claude-code/opus-5.5
  at: "2026-10-31T15:00:00+07:00"
stale_after: "2027-01-29T15:00:00+07:00"
lifecycle: local source / live dependency
project: n8n-nodes-mezon
class: none
owner: dungxbuif
repo: local Git only; GitLab not configured
deployed_revision: live package remains unchanged during local workflow work
---

# n8n-nodes-mezon

## Summary

n8n community node package: Mezon (bot SDK), Mezon Channel Webhook and Mezon Trigger. A packed `n8n-nodes-mezon-0.1.0.tgz` sits in the folder.

Class `none` · owner dungxbuif · status `local source / live dependency`.

## Source

| Field | Value |
|---|---|
| Local checkout | `/home/dungxbuif/workspace/projects/n8n-nodes-mezon/` |
| Git | local branch `codex/gold-price-hanoi-fallback` |
| GitLab | not configured |
| Repo docs | `README.md` |
| Deployed revision | existing live package; no new package deployed in this change |

## Why it does not run

Not a service, but **in use**: `n8n-nodes-mezon` is installed in the live n8n data dir (`/opt/apps/n8n/data/nodes/node_modules/`, VM100). See [n8n](../services/n8n.md). The project now has a local Git boundary; no remote or live package update was performed.

## Hanoi gold-price workflow

Canonical local files:

- `gold-price-hanoi/runtime.cjs`: source registry, brand-specific aliases, parsers, unit conversion, fallback, snapshot diffing.
- `gold-price-hanoi/run-local.cjs`: local live runner; it never sends to Mezon.
- `examples/generate-gold-price-hanoi-workflow.cjs`: inactive n8n test workflow generator.
- `docs/superpowers/specs/2026-10-31-gold-price-hanoi-fallback-design.md`: design and source policy.
- `docs/superpowers/plans/2026-10-31-gold-price-hanoi-fallback.md`: implementation checklist.

Scope is exactly `gold_bar` and `round_ring` for BTMC, BTMH, DOJI, PNJ, Phú Quý,
and SJC. The generated workflow uses twelve primary/fallback gold source nodes
plus the retained Petrolimex fuel node, reports daily at 08:00, and checks gold
changes every ten minutes during 08:00–21:00. The daily report keeps RON 95,
E5 RON 92, and Diesel V1/V2; the watcher remains gold-only.
The six brand branches run in parallel and merge before normalization; fallback
within each brand remains conditional.
SJC Cloudflare/HTTP block and incomplete source rows remain visible as source
diagnostics. They are not converted into prices.
The missing-data warning is emitted only when all configured candidates for a
source fail; a successful fallback suppresses it. The watcher shares the gold
source chain but skips the Petrolimex fetch.
The n8n parser persists a last-good two-row result per brand for up to six hours
through transient source failures; it preserves the older source update time
and only falls back to `N/A` after that cache window expires. All rendered
timestamps use `DD/MM/YYYY HH:mm`; the daily title uses `DD/MM/YYYY`.

Delivery separation is mandatory: local/dev uses `MEZON_GOLD_TEST_WEBHOOK_URL`;
production uses the separately managed `MEZON_GOLD_PROD_WEBHOOK_URL`. Neither
secret is stored in this repository or its generated JSON.

## Verification and backup evidence (2026-10-31)

- Local unit/integration tests: `16/16` passed.
- Latest independent official-source run: BTMC primary returned HTTP 404 without a configured API key, then the official `btmc.vn` HTML fallback returned both target products; BTMH, DOJI, PNJ, and Phú Quý returned both target products; SJC was blocked with HTTP 403 on both direct candidates; Petrolimex returned the retained three-row fuel section.
- A browser session can load the official SJC page and show the exact two target rows, but the current n8n HTTP code path receives Cloudflare 403; no unverified third-party source was substituted.
- A free headless Chrome trial (the route intended for an n8n `Execute Command` node) also received the Cloudflare challenge, so it is not treated as an automated source yet. A browser-session snapshot was used only for the DEV preview: SJC bar `13.600 / 13.900`, round ring `13.180 / 13.580`, source update `31/10/2026 08:16`.
- First watcher decision: `baseline-initialized`, `send=false`.
- Final DEV preview re-sent after the parser/cache/time-format fixes with the production-compatible envelope and `message.mk = [{ type: "pre", s: 0, e: message.t.length }]`; HTTP 200 accepted, 5/6 gold brands had two rows, Petrolimex was OK, and only SJC produced the expected missing-source warning. Production webhook was not called.
- Additional DEV preview with the official browser-session SJC snapshot: HTTP 200 accepted, 6/6 gold brands had two rows, no missing-data warning. This was a preview only; no production workflow or persistent n8n source was changed.
- Live workflow backup made over SSH before any import: `/tmp/n8n-gold-before-hanoi-local-test.1yfONB.json`, 25,412 bytes, workflow `daily-gold-fuel-mezon`, 8 nodes, active. The backup is outside the repository and contains the old workflow snapshot; do not commit it.
- No n8n import, activation, production delivery, or production webhook use occurred.
