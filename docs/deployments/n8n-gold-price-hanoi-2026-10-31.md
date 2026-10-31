---
type: Deployment
title: n8n Hanoi gold-price workflow — local/dev verification
generated:
  by: codex
  at: "2026-10-31T13:00:00+07:00"
stale_after: "2026-11-30T13:00:00+07:00"
lifecycle: verification-only
service: n8n
---

# n8n Hanoi gold-price workflow — local/dev verification

## Decision

The new workflow is local/dev only. It has not been imported, activated, or
sent to either Mezon destination. Production remains separate and requires a
later explicit release approval.

## Scope and source policy

The workflow reads only two product families for each brand: gold bars and
round rings. It uses official primary/fallback candidates for BTMC, Bảo Tín
Mạnh Hải, DOJI, PNJ, Phú Quý, and SJC. Brand-specific aliases and units are
implemented in the project runtime; all output is normalized to VND/lượng while
retaining the source unit in row metadata.

The schedule contract is:

- daily report: `0 8 * * *`
- watcher: `*/10 8-21 * * *`

The watcher establishes a baseline on its first run, then sends only price or
source-status changes. The daily report always sends the full diagnostic table.

## Root cause addressed

The live workflow `daily-gold-fuel-mezon` had two schedule paths sharing one
Mezon node with a hard-coded destination. That allowed a channel change or
workflow merge to move both the daily and watcher messages to the wrong
channel. There was also no versioned canonical source for the merged workflow.

The generated workflow separates the runtime destination into
`MEZON_GOLD_TEST_WEBHOOK_URL` (dev/test) and `MEZON_GOLD_PROD_WEBHOOK_URL`
(production). The production value is not written here or into repository
files.

## Evidence

- `npm test`: 7 tests passed.
- `npm run typecheck`: passed after `npm ci`.
- `npm run build`: passed.
- Dev/test delivery was sent once after local verification and accepted with HTTP 200. This is awaiting human inspection; production delivery was not called.
- Local live run was performed without sending to Mezon:
  - BTMC: primary OK, two products.
  - DOJI: primary OK, two products; encrypted API payload decrypted locally.
  - PNJ: primary OK, Hanoi data plus generic ring table, two products.
  - Phú Quý: primary OK, two products.
  - BTMH: both official candidates incomplete because the live round-ring row
    has no sell value; failed closed.
  - SJC: both official candidates HTTP 403; reported blocked.
  - first watcher: baseline only, `send=false`.
- Current live workflow export backup: `/tmp/n8n-gold-before-hanoi-local-test.1yfONB.json` on the local machine, 25,412 bytes, workflow ID `daily-gold-fuel-mezon`, active with 8 nodes.

## Release gate

Do not import or activate the generated workflow until:

1. BTMH round-ring sell price is confirmed or intentionally accepted as
   unavailable.
2. A dev webhook is supplied through `MEZON_GOLD_TEST_WEBHOOK_URL` and the
   test delivery is manually inspected.
3. The generated JSON is reviewed for node connections and no secrets.
4. The live export backup remains recoverable and rollback is tested.

