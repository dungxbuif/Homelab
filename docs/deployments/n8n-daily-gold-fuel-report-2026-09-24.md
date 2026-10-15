---
type: Deployment
title: "n8n Daily Gold And Fuel Mezon Report"
description: "Production workflow config for the 08:00 daily BTMC, BTMH, and Petrolimex Mezon report"
timestamp: 2026-09-24T00:00:00+07:00
---

# n8n Daily Gold And Fuel Mezon Report

## Runtime

| Field | Value |
|---|---|
| n8n host | `https://n8n.dungxbuif.com` |
| Workflow name | `Daily Gold & Fuel Report to Mezon` |
| Workflow ID | `daily-gold-fuel-mezon` |
| Schedule | `0 8 * * *` |
| Timezone | `Asia/Ho_Chi_Minh` |
| Output | Mezon channel webhook message |
| Format | One `pre` block with Vietnamese text and aligned columns |
| AI/LLM usage | None |

The workflow is deterministic. It fetches source pages, parses fixed product
markers, formats the report, and sends the webhook. Do not add an LLM node to
this workflow unless the report becomes intentionally editorial or summarizing.

## Workflow Nodes

| Node | Purpose |
|---|---|
| `Manual Trigger` | Manual entrypoint; shares daily idempotency with the scheduled path. |
| `Every day at 08:00` | Production cron entrypoint. |
| `Check daily idempotency` | Stops manual or scheduled runs when `lastSentDate` already equals today's date. |
| `Fetch prices and build report` | Fetches/parses BTMC, BTMH, e10.vn, and Webgia; builds Mezon payload. |
| `Mezon Webhook` | Sends the payload to the endpoint configured directly on this node. |
| `Mark sent after Mezon success` | Runs only after webhook success, then writes `lastSentDate`, `previousPrices`, and `lastSuccessfulSentAt`. |
| `Note` | In-canvas operator note. |

## Editable Config

The Mezon channel endpoint is configured directly on the `Mezon Webhook` node
in its masked `Endpoint URL` field. To change the destination, open the node
and edit that field. Both the manual and scheduled paths use the same node.

The production endpoint was migrated from the previous credential to the node
field without changing its value. The actual URL is a secret and must not be
committed to this repository or copied into workflow source files.

## Idempotency

Manual and scheduled runs are idempotent by local date:

- Key: `lastSentDate`
- Scope: n8n workflow static data
- Date format: `dd/mm/yyyy`, timezone `Asia/Ho_Chi_Minh`
- Both paths skip silently by returning no items when already sent today

The workflow marks a day as sent only after Mezon webhook delivery succeeds.
If source fetch/parsing fails or Mezon rejects the request, `lastSentDate` is
not updated and the next scheduled/manual attempt can retry.

`previousPrices` is also updated only after a successful send. This makes the
increase/decrease arrows compare against the last successfully delivered report,
not against a failed attempt.

## Sources And Products

| Source | URL | Parsed rows |
|---|---|---|
| BTMC | `https://btmc.vn/` | `Vàng miếng VRTL BTMC`, `Nhẫn tròn trơn BTMC`, `Vàng miếng SJC`, `Trang sức VRTL 999.9` |
| BTMH | `https://baotinmanhhai.vn/bang-gia-vang` | `Kim Gia Bảo 24K`, `Vàng miếng SJC`, `Vàng nguyên liệu 999.9` |
| E10 fuel | `https://e10.vn/gia` | `Xăng E10 RON 95-III` |
| Webgia Petrolimex | `https://webgia.com/gia-xang-dau/petrolimex/` | `Xăng E5 RON 92-II`, `Dầu hỏa 2-K` |

Fuel report policy:

- Only Vùng 1 prices are reported.
- The report includes the note `Chú thích: chỉ lấy giá Vùng 1.`
- E10 RON 95-III comes from e10.vn because the Webgia Petrolimex table did not
  expose E10 in the checked production page.

## Failure Policy

Parsing is intentionally strict. Missing source markers throw an error instead
of sending stale or guessed prices.

Expected operator response:

1. Open the failed execution in n8n.
2. Check which marker/source failed.
3. Update parser logic only after verifying the source page changed.
4. Re-run through `Manual Trigger`.

## Deployment Artifacts

The generator used to create/import the workflow lives outside this homelab
repo:

`/Users/dungxbuif/workspace/n8n-nodes-mezon/examples/generate-price-workflow.cjs`

The standalone parser POC lives at:

`/Users/dungxbuif/workspace/n8n-nodes-mezon/examples/prod-price-report.cjs`

The generator contains only the n8n credential reference; the webhook URL is
stored encrypted in the n8n credential store.

## Verification On 2026-09-24

- Workflow imported into n8n with ID `daily-gold-fuel-mezon`.
- Workflow activated/published through n8n CLI.
- Destination configured in the `Endpoint URL` field on the `Mezon Webhook`
  node; existing production URL retained during migration.
- n8n task restarted so the 08:00 scheduler loads the new active workflow.
- VM100 n8n container healthy after restart.
- `https://n8n.dungxbuif.com/healthz` returned `200`.
