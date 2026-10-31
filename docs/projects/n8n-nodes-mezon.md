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
and SJC. The generated workflow uses twelve primary/fallback source nodes,
reports daily at 08:00, and checks changes every ten minutes during 08:00–21:00.
SJC Cloudflare/HTTP block and incomplete source rows remain visible as source
diagnostics. They are not converted into prices.

Delivery separation is mandatory: local/dev uses `MEZON_GOLD_TEST_WEBHOOK_URL`;
production uses the separately managed `MEZON_GOLD_PROD_WEBHOOK_URL`. Neither
secret is stored in this repository or its generated JSON.

## Verification and backup evidence (2026-10-31)

- Local unit/integration tests: `7/7` passed.
- Local official-source run: BTMC, DOJI, PNJ, and Phú Quý returned both target products; BTMH returned an incomplete round-ring row and was failed closed; SJC was blocked with HTTP 403 on both official candidates.
- First watcher decision: `baseline-initialized`, `send=false`.
- Dev/test delivery sent once after local verification: HTTP 200 accepted by the test webhook; production webhook was not called. Awaiting human inspection/approval.
- Live workflow backup made over SSH before any import: `/tmp/n8n-gold-before-hanoi-local-test.1yfONB.json`, 25,412 bytes, workflow `daily-gold-fuel-mezon`, 8 nodes, active. The backup is outside the repository and contains the old workflow snapshot; do not commit it.
- No n8n import, activation, production delivery, or production webhook use occurred.
