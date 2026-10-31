---
type: Deployment
title: n8n Hanoi gold-price workflow — production release
generated:
  by: codex
  at: "2026-10-31T13:56:30+07:00"
stale_after: "2026-11-30T13:00:00+07:00"
lifecycle: active
service: n8n
---

# n8n Hanoi gold-price workflow — production release

## Decision

The approved production release is live in n8n. The workflow uses the runtime
variable `MEZON_GOLD_PROD_WEBHOOK_URL`; the webhook token is not in this
repository, generated JSON, or this document. The release did not send a
manual production test message; scheduled delivery is the production smoke
path.

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

## Production release record

- Source revision: `3be86b3` (`feat: add production workflow release mode`).
- Live workflow ID: `daily-gold-fuel-mezon`.
- Published name: `Hanoi Gold Price Fallback - PROD`.
- Published shape: 22 nodes; six parallel brand branches, twelve gold source
  slots, Petrolimex daily branch, seven-input merge, conditional fallbacks.
- Schedules: daily `0 8 * * *`; watcher `*/10 8-21 * * *`.
- Import path: `n8n import:workflow` with the existing workflow ID, then
  `n8n publish:workflow --id=daily-gold-fuel-mezon`; a controlled `n8n` service
  restart was performed because this n8n instance is regular mode.
- Runtime destination identity was checked by hostname/path only; the secret
  value was never printed. The custom `mezonWebhook` node is installed in the
  live package (`n8n-nodes-mezon` 0.1.1).

## Evidence

- `npm test`: 17 tests passed.
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
- Pre-import live workflow export backup: `/opt/apps/n8n/data/backups/n8n-gold-before-hanoi-prod-20261031T065023+0000.json` on VM100, 25,412 bytes, mode `600`, workflow ID `daily-gold-fuel-mezon`, active with 8 nodes. Post-import and published exports are retained beside it.
- Release verification: after the publish, the n8n container was force-restarted and reported `healthy`, restart count `0`; local and public `/healthz` returned `{"status":"ok"}`. The published export reported `active: true`, 22 nodes, and the production env expression.

## Release gate — completed

1. SJC official-source `blocked`/`N/A` behavior was intentionally accepted;
   no unapproved third-party source was added.
2. DEV preview was accepted earlier with the production-compatible Mezon
   envelope; production delivery was kept schedule-driven for this release.
3. Generated production JSON was reviewed: 22 nodes, both schedules, correct
   connections, runtime env expression, and no webhook literal.
4. The pre-import backup is protected and recoverable. Rollback is:

   ```sh
   cid=$(docker ps --filter name='n8n.1' --format '{{.ID}}' | head -1)
   docker cp /opt/apps/n8n/data/backups/n8n-gold-before-hanoi-prod-20261031T065023+0000.json "$cid":/tmp/gold-rollback.json
   docker exec "$cid" n8n import:workflow --input=/tmp/gold-rollback.json
   docker exec "$cid" n8n publish:workflow --id=daily-gold-fuel-mezon
   docker service update --force n8n
   ```

