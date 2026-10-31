---
type: Project
title: n8n-nodes-mezon
description: n8n community nodes for Mezon; installed in the running n8n
generated:
  by: claude-code/opus-5.5
  at: "2026-10-31T14:10:19+07:00"
stale_after: "2027-01-29T15:00:00+07:00"
lifecycle: local source / live dependency
project: n8n-nodes-mezon
class: none
owner: dungxbuif
repo: local Git checkout; no remotes configured
deployed_revision: "faaf3cc (SJC removed from active report); follow-up docs a4bed9a and cleanup 423fe77"
---

# n8n-nodes-mezon

## Summary

n8n community node package: Mezon (bot SDK), Mezon Channel Webhook and Mezon Trigger. A packed `n8n-nodes-mezon-0.1.0.tgz` sits in the folder.

Class `none` · owner dungxbuif · status `local source / live dependency`.

## Source

| Field | Value |
|---|---|
| Local checkout | `/home/dungxbuif/workspace/projects/n8n-nodes-mezon/` |
| Git | local branch `codex/gold-price-hanoi-fallback`, clean at `423fe77` |
| Git remotes | none configured; do not invent a remote until the GitLab project is created |
| Repo docs | `README.md` |
| Deployed revision | workflow `daily-gold-fuel-mezon` from `faaf3cc` plus earlier hotfixes; package `0.1.1` unchanged |

## Why it does not run

Not a service, but **in use**: `n8n-nodes-mezon` is installed in the live n8n data dir (`/opt/apps/n8n/data/nodes/node_modules/`, VM100). See [n8n](../services/n8n.md). The gold workflow uses the installed `mezonWebhook` node; the package itself was not replaced during this release.

## Hanoi gold-price workflow

Canonical local files:

- `gold-price-hanoi/runtime.cjs`: source registry, brand-specific aliases, parsers, unit conversion, fallback, snapshot diffing.
- `gold-price-hanoi/run-local.cjs`: local live runner; it never sends to Mezon.
- `examples/generate-gold-price-hanoi-workflow.cjs`: inactive TEST generator by default; `--prod` emits the approved active production artifact using a runtime env variable.
- `docs/superpowers/specs/2026-10-31-gold-price-hanoi-fallback-design.md`: design and source policy.
- `docs/superpowers/plans/2026-10-31-gold-price-hanoi-fallback.md`: implementation checklist.

Active report scope is exactly `gold_bar` and `round_ring` for BTMC, BTMH, DOJI,
PNJ, and Phú Quý. The generated production workflow uses ten primary/fallback
gold source nodes plus the retained Petrolimex fuel node, reports daily at
08:00, and checks gold changes every ten minutes during 08:00–21:00. The daily
report keeps RON 95, E5 RON 92, and Diesel V1/V2; the watcher remains gold-only.
The five brand branches run in parallel and merge before normalization; fallback
within each brand remains conditional. SJC parser fixtures remain in the source
registry for regression coverage, but SJC is excluded from collection, parsing
of active results, and production output.
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

- Local unit/integration tests: `20/20` passed; `npm run typecheck`, `npm run build`, and `git diff --check` passed.
- Latest independent official-source run: BTMC primary returned HTTP 404 without a configured API key, then the official `btmc.vn` HTML fallback returned both target products; BTMH, DOJI, PNJ, and Phú Quý returned both target products; SJC was blocked with HTTP 403 on both direct candidates; Petrolimex returned the retained three-row fuel section.
- A browser session can load the official SJC page and show the exact two target rows, but the current n8n HTTP code path receives Cloudflare 403; no unverified third-party source was substituted.
- A free headless Chrome trial (the route intended for an n8n `Execute Command` node) also received the Cloudflare challenge, so it is not treated as an automated source yet. A browser-session snapshot was used only for the DEV preview: SJC bar `13.600 / 13.900`, round ring `13.180 / 13.580`, source update `31/10/2026 08:16`.
- First watcher decision: `baseline-initialized`, `send=false`.
- Final DEV preview re-sent after the parser/cache/time-format fixes with the production-compatible envelope and `message.mk = [{ type: "pre", s: 0, e: message.t.length }]`; HTTP 200 accepted, 5/6 gold brands had two rows, Petrolimex was OK, and only SJC produced the expected missing-source warning. Production webhook was not called.
- Additional DEV preview with the official browser-session SJC snapshot: HTTP 200 accepted, 6/6 gold brands had two rows, no missing-data warning. This was a preview only; no production workflow or persistent n8n source was changed.
- Production release: commit `3be86b3`, workflow `daily-gold-fuel-mezon`, imported and published on VM100 as `Hanoi Gold Price Fallback - PROD`, active, 22 nodes, with daily `0 8 * * *` and watcher `*/10 8-21 * * *` schedules. The delivery node reads only `MEZON_GOLD_PROD_WEBHOOK_URL` at runtime.
- Hotfix `d4a78dd` removes `process.env` from the BTMC primary Code node. n8n's external JavaScript runner does not expose `process`; the node now uses the official static BTMC API URL and keeps the existing conditional fallback path.
- Hotfix backup before import: `/opt/apps/n8n/data/backups/n8n-gold-before-btmc-runner-fix-20261031T070632+0000.json`, 249,098 bytes, mode `600`. Final published export: `/opt/apps/n8n/data/backups/n8n-gold-btmc-fix-final.json`, 249,072 bytes, mode `600`.
- Post-hotfix verification: published workflow `active=true`, 22 nodes, BTMC primary `process` reference absent, production destination remains `={{ $env.MEZON_GOLD_PROD_WEBHOOK_URL }}`, n8n task healthy with restart count `0`, and local/public `/healthz` returned `{"status":"ok"}`.
- Runner follow-up: the first post-hotfix trace found `DisallowedModuleError: Module 'node:crypto' is disallowed` because the main n8n service had the built-in allow-list but `n8n-runners` did not. The Swarm runner service now has `NODE_FUNCTION_ALLOW_BUILTIN=crypto,net,dns,https,url`, is `1/1`, and produced no fresh disallowed-module error after restart.
- The CLI execution smoke attempt remains inconclusive because a temporary CLI process cannot bind task-broker port `5679` while the live n8n process owns it; no manual production webhook was sent.
- Pre-import live backup: `/opt/apps/n8n/data/backups/n8n-gold-before-hanoi-prod-20261031T065023+0000.json` on VM100, 25,412 bytes, mode `600`, old workflow active with 8 nodes. Post-import and published exports are retained in the same protected `backups/` directory.
- n8n was force-restarted after CLI publish; VM100 container reported `healthy`, restart count `0`, and `/healthz` returned `{"status":"ok"}` locally and through `https://n8n.dungxbuif.com/healthz`.
- No manual production webhook message was sent during release; the first production delivery is schedule-driven. SJC remains an explicit official-source `blocked`/`N/A` condition until an approved automated access strategy is added; no third-party price source was substituted.

### SJC alternative-source decision record — 2026-10-31

- Official SJC remains the only source allowed to populate the canonical SJC
  bar/ring rows. The official page lists both product families, but VM100's
  automated HTTP path is blocked by the site's WAF/Cloudflare layer.
- DOJI, PNJ, and Phú Quý officially publish an SJC bar row, so they are viable
  **reference** sources for a separately labeled bar value. Their ring rows are
  their own products, not `Nhẫn tròn SJC`, and cannot be used as a silent SJC
  fallback.
- A third-party aggregator or browser-session collector could cover the missing
  ring value, but neither is approved for production automation yet. Current
  behavior remains `blocked` → `N/A` after the last-good cache expires.
- No live workflow, webhook, credential, or production payload was changed by
  this source audit.

### Current production removal — 2026-10-31

- User-approved commit `faaf3cc` removed SJC from the active production report.
- Protected pre-change export: `/opt/apps/n8n/data/backups/n8n-gold-before-remove-sjc-20261031T075959+0000.json` (245,400 bytes, mode `600`).
- Published export: `/opt/apps/n8n/data/backups/n8n-gold-remove-sjc-final-20261031T0810+0000.json` (213,856 bytes, mode `600`).
- Verification: active workflow, 20 nodes, five gold branches plus Petrolimex,
  merge input count 6, no `Fetch SJC` node, runtime delivery env unchanged,
  public health `{"status":"ok"}`.
- No manual production webhook was sent during this change.

### Workflow identity collision audit — 2026-10-31

- The deleted legacy generator `examples/generate-price-workflow.cjs` used the
  same n8n ID `daily-gold-fuel-mezon` as production but generated the old
  `Daily Gold & Fuel Report to Mezon` 7-node workflow.
- The VM100 historical snapshot with that ID remains protected for rollback;
  it is not a deployment input.
- The canonical generator does not emit the production ID, and the active
  production export was verified as `Hanoi Gold Price Fallback - PROD`, active,
  20 nodes, five brands, with both existing schedules.
- No live homelab import job or n8n workflow mutation event was found. The
  proven failure mode is last-import-wins identity collision; the earlier
  trigger is not proven to be an automatic job.

Read-only comparison on 2026-10-31: DOJI and PNJ both returned SJC bar
`136.000.000 / 139.000.000` (VND/lượng); Phú Quý returned
`134.500.000 / 139.000.000`, so the buy side is not uniform. Calc.vn also
returned `136.000.000 / 139.000.000`, but is non-primary. The only separately
found SJC-ring value (`131.800.000 / 135.800.000`) came from a third-party
aggregator and is not approved. No production source was changed.
