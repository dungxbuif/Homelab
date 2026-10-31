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

The watcher establishes a baseline on its first run, then sends only gold price
or source-status changes. The daily report always sends the full gold table and
retains the existing Petrolimex RON 95/E5/Diesel V1/V2 section.
Rendered timestamps are normalized to `DD/MM/YYYY HH:mm` (daily title:
`DD/MM/YYYY`). The n8n parser persists each brand's last valid two-row result
for up to six hours across transient source failures, keeping the source's
older update time visible; after expiry it emits `N/A` and the missing-source
warning.

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

- `npm test`: 16 tests passed.
- `npm run typecheck`: passed after `npm ci`.
- `npm run build`: passed.
- Final DEV preview after the BTMC fallback, source-cache, and timestamp fixes used the current production-compatible Mezon format (`message.mk` contains one `pre` range covering all of `message.t`) and was accepted with HTTP 200. The payload had 5/6 gold brands with two rows, Petrolimex OK, and only SJC's expected blocked-source warning. Production delivery was not called.
- Latest local live run was performed without sending to Mezon and checked each brand independently:
  - BTMC: primary HTTP 404 without an API key; official `btmc.vn` HTML fallback OK, two products.
  - DOJI: primary OK, two products; encrypted API payload decrypted locally.
  - PNJ: primary OK, Hanoi data plus generic ring table, two products.
  - Phú Quý: primary OK, two products.
  - BTMH: primary embedded production data parsed successfully, two products.
  - SJC: both official candidates HTTP 403; reported blocked.
  - Petrolimex: daily fuel section returned three V1/V2 rows.
  - first watcher: baseline only, `send=false`.
- The official SJC page loads in a browser session and exposes the exact bar and
  round-ring rows, but the n8n HTTP path is still challenged with HTTP 403. No
  unverified third-party source was added to hide that condition.
- Free headless Chrome was tested as the planned `Execute Command` integration;
  it also received the Cloudflare challenge. A browser-session-only DEV preview
  was sent with SJC values `13.600/13.900` and `13.180/13.580`, source update
  `31/10/2026 08:16`, and HTTP 200. It is not production automation.
- Current live workflow export backup: `/tmp/n8n-gold-before-hanoi-local-test.1yfONB.json` on the local machine, 25,412 bytes, workflow ID `daily-gold-fuel-mezon`, active with 8 nodes.

## Release gate

Do not import or activate the generated workflow until:

1. SJC browser/session strategy is confirmed or the official-source N/A state
   is intentionally accepted.
2. A dev webhook is supplied through `MEZON_GOLD_TEST_WEBHOOK_URL` and the
   test delivery is manually inspected.
3. The generated JSON is reviewed for node connections and no secrets.
4. The live export backup remains recoverable and rollback is tested.

