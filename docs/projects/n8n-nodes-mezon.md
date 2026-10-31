---
type: Project
title: n8n-nodes-mezon
description: n8n community nodes for Mezon; installed in the running n8n
generated:
  by: claude-code/opus-5.5
  at: "2026-10-31T13:56:30+07:00"
stale_after: "2027-01-29T15:00:00+07:00"
lifecycle: local source / live dependency
project: n8n-nodes-mezon
class: none
owner: dungxbuif
repo: local Git only; GitLab not configured
deployed_revision: "3be86b3 (workflow release; live package 0.1.1 unchanged)"
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
| Deployed revision | workflow `daily-gold-fuel-mezon` from `3be86b3`; package `0.1.1` unchanged |

## Why it does not run

Not a service, but **in use**: `n8n-nodes-mezon` is installed in the live n8n data dir (`/opt/apps/n8n/data/nodes/node_modules/`, VM100). See [n8n](../services/n8n.md). The gold workflow uses the installed `mezonWebhook` node; the package itself was not replaced during this release.

## Hanoi gold-price workflow

Canonical local files:

- `gold-price-hanoi/runtime.cjs`: source registry, brand-specific aliases, parsers, unit conversion, fallback, snapshot diffing.
- `gold-price-hanoi/run-local.cjs`: local live runner; it never sends to Mezon.
- `examples/generate-gold-price-hanoi-workflow.cjs`: inactive TEST generator by default; `--prod` emits the approved active production artifact using a runtime env variable.
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

- Local unit/integration tests: `17/17` passed; `npm run typecheck`, `npm run build`, and `git diff --check` passed.
- Latest independent official-source run: BTMC primary returned HTTP 404 without a configured API key, then the official `btmc.vn` HTML fallback returned both target products; BTMH, DOJI, PNJ, and Phú Quý returned both target products; SJC was blocked with HTTP 403 on both direct candidates; Petrolimex returned the retained three-row fuel section.
- A browser session can load the official SJC page and show the exact two target rows, but the current n8n HTTP code path receives Cloudflare 403; no unverified third-party source was substituted.
- A free headless Chrome trial (the route intended for an n8n `Execute Command` node) also received the Cloudflare challenge, so it is not treated as an automated source yet. A browser-session snapshot was used only for the DEV preview: SJC bar `13.600 / 13.900`, round ring `13.180 / 13.580`, source update `31/10/2026 08:16`.
- First watcher decision: `baseline-initialized`, `send=false`.
- Final DEV preview re-sent after the parser/cache/time-format fixes with the production-compatible envelope and `message.mk = [{ type: "pre", s: 0, e: message.t.length }]`; HTTP 200 accepted, 5/6 gold brands had two rows, Petrolimex was OK, and only SJC produced the expected missing-source warning. Production webhook was not called.
- Additional DEV preview with the official browser-session SJC snapshot: HTTP 200 accepted, 6/6 gold brands had two rows, no missing-data warning. This was a preview only; no production workflow or persistent n8n source was changed.
- Production release: commit `3be86b3`, workflow `daily-gold-fuel-mezon`, imported and published on VM100 as `Hanoi Gold Price Fallback - PROD`, active, 22 nodes, with daily `0 8 * * *` and watcher `*/10 8-21 * * *` schedules. The delivery node reads only `MEZON_GOLD_PROD_WEBHOOK_URL` at runtime.
- Pre-import live backup: `/opt/apps/n8n/data/backups/n8n-gold-before-hanoi-prod-20261031T065023+0000.json` on VM100, 25,412 bytes, mode `600`, old workflow active with 8 nodes. Post-import and published exports are retained in the same protected `backups/` directory.
- n8n was force-restarted after CLI publish; VM100 container reported `healthy`, restart count `0`, and `/healthz` returned `{"status":"ok"}` locally and through `https://n8n.dungxbuif.com/healthz`.
- No manual production webhook message was sent during release; the first production delivery is schedule-driven. SJC remains an explicit official-source `blocked`/`N/A` condition until an approved automated access strategy is added; no third-party price source was substituted.
