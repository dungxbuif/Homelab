---
type: Deployment
title: n8n Hanoi gold-price workflow — production release
generated:
  by: codex
  at: "2026-10-31T14:10:19+07:00"
stale_after: "2026-11-30T13:00:00+07:00"
lifecycle: active
service: n8n
---

# n8n Hanoi gold-price workflow — production release

## Decision

The approved production release, BTMC runner hotfix, and external-runner allow-list fix are live in n8n. The workflow uses the runtime
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
- Hotfix revision: `d4a78dd` (`fix: remove process dependency from gold source node`).
- Runtime configuration fix: `n8n-runners` now receives
  `NODE_FUNCTION_ALLOW_BUILTIN=crypto,net,dns,https,url`, matching the main n8n
  service's Code-node allow-list.
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

- `npm test`: 18 tests passed, including the regression assertion that generated
  source nodes do not reference `process` in n8n's external runner.
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
- Hotfix pre-import backup: `/opt/apps/n8n/data/backups/n8n-gold-before-btmc-runner-fix-20261031T070632+0000.json`, 249,098 bytes, mode `600`. Final published export: `/opt/apps/n8n/data/backups/n8n-gold-btmc-fix-final.json`, 249,072 bytes, mode `600`.
- Hotfix verification: the published export reported `active: true`, 22 nodes, no `process.` reference in `Fetch BTMC primary`, and the production destination remained `={{ $env.MEZON_GOLD_PROD_WEBHOOK_URL }}`. After a forced restart, the n8n container reported `healthy`, restart count `0`; local and public `/healthz` returned `{"status":"ok"}`.
- External-runner verification: the first runtime trace exposed
  `DisallowedModuleError: Module 'node:crypto' is disallowed`; the main n8n
  service already allowed built-ins but `n8n-runners` did not. After
  `docker service update --env-add NODE_FUNCTION_ALLOW_BUILTIN=crypto,net,dns,https,url n8n-runners`, runners returned to `1/1`; the new runner has the
  allow-list and no fresh disallowed-module error in the observation window.

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

## Post-release UI incident — 2026-10-31 14:02 ICT

- Chrome reproduced `ERR_NETWORK_CHANGED`; n8n showed `Init Problem: Network
  Error`, `Offline`, and `Can't connect to n8n`.
- This was not a backend outage: shell probes returned HTTP 200 for public
  `/healthz`, `/rest/settings`, and `/`; the n8n container remained healthy.
- Traefik access logs showed n8n API requests completing with `200`/`304`, while
  the failing browser bursts were client-aborted `499` requests and closed
  `/rest/push` long-poll connections. This identifies the failure boundary as
  the Chrome/host network path, not the workflow database or production
  webhook.
- Host NetBird status was Management/Signal connected but only `1/2` peers
  connected; the gateway also logged repeated 60-second NetBird management
  `504` jobs. No n8n rollback was performed for this client-side incident.
- Separate follow-up found in the manual production execution: the BTMC
  primary Code node referenced `process.env`, but n8n's external JavaScript
  runner does not expose `process`. This was a workflow execution defect,
  independent of the browser `Network Error`; hotfix `d4a78dd` replaced it with
  the official static BTMC API URL, then the workflow was backed up, imported,
  published, restarted, and verified active/healthy.
- A requested one-shot CLI execution was attempted twice; both stopped before
  workflow execution because the temporary CLI process tried to bind task
  broker port `5679`, already owned by the live n8n process. No successful
  production delivery was confirmed from these attempts; do not count them as
  a smoke-test pass.

## Follow-up network and runner trace — 2026-10-31 14:15 ICT

- A fresh Chrome tab loaded the n8n workflow list and showed `Hanoi Gold Price
  Fallback - PROD`; the UI was not currently failing with `Network Error`.
- Traefik probes from the shell returned `200` for `/`, `/healthz`, and
  `/rest/settings`. The earlier browser burst was client-aborted `499`; the
  same period contained NetBird management `504` jobs. NetBird itself is
  connected to management/signal, both relays are available, and the active
  ThinkPad peer has a recent WireGuard handshake; the idle Mac peer explains
  `1/2` connected and is not an n8n outage.
- The runner `node:crypto` failure was a separate execution configuration
  defect and is now fixed. No workflow logic, webhook destination, or
  production message was changed by this follow-up, and no manual production
  webhook was sent.

