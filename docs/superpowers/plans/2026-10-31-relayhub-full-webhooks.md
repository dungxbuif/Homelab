---
type: Plan
title: RelayHub Full Webhooks Implementation Plan
generated:
  by: "process:vault-import"
  at: "2026-10-31T16:00:00+07:00"
stale_after: "2026-12-30T16:00:00+07:00"
---

# RelayHub Full Webhooks Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete inbound webhook tunneling and restore signed outbound callbacks, routing and safe DLQ replay in Rust v1.

**Architecture:** Extend existing PostgreSQL event/delivery authority with immutable targets and agent/callback sinks. Keep transactional acceptance, quota accounting, outbox and fenced settlement; callback workers use a separate sink while dashboards/SDKs share lifecycle contracts. Users integrate against a managed RelayHub instance.

**Tech Stack:** Rust/Axum/sqlx/reqwest, PostgreSQL, NATS JetStream, Redis, Node/Go SDKs, React/Playwright and disposable integration services.

**Spec:** [Full webhook design](../specs/2026-10-31-relayhub-full-webhooks-design.md), with Rust v1 baseline (RelayHub v1 design, in git history) limits. This explicitly restores original outbound callbacks/routing as new v1 work; it does not imply all old Go features are in scope.

## Global Constraints

- Preserve v1 body maximum 1 MiB, seven-day event retention, 10,000 outstanding deliveries and 100 MiB outstanding payload bytes per workspace.
- Preserve sync timeout default 15 seconds, allowed 1–30 seconds; offline `queue`/`reject` and timeout `continue`/`expire_pending` behavior.
- Callback HTTP method is POST, timeout 10 seconds, response read cap 1 MiB.
- Five attempts total with base delays `1,5,30,120` seconds, matching v1.
- Maximum 32 unique targets per event, deduplicated by `(target_app,sink)`; reject overflow before commit.
- Replay batch contains 1–100 distinct explicit IDs, validated atomically; no implicit replay-all.
- PostgreSQL acceptance, quota charge, target deliveries and outbox commit atomically before `202`. At least once; no exactly-once promise.
- Preserve unrelated dirty OpenAPI/acceptance work and the separately paused Rust completion task. New code stays in the RelayHub project; no production migration/restart during implementation tests.

## Review Focus

1. Fan-out changes ownership checks or charges only one target — W2 must enforce tenant isolation and atomic per-target quota accounting.
2. Another routed agent answers a synchronous request or an expired lease completes a replay — W2/W4/W5 must fence both target and generation.
3. Callback URLs redirect/rebind to private services or error logs leak query tokens — W3 must validate the actual connection and redact sensitive data.
4. Secret rotation, raw body encoding or escaped query order breaks verification — W3/W4/W6 must preserve signed bytes and explicit key versions.
5. A repeated replay or dashboard test causes duplicate deliveries — W1/W2/W5/W6 must reuse request identity and return existing results.

---

## File map and interfaces

Paths are relative to `/home/dungxbuif/workspace/projects/RelayHub`. Work in an isolated parent worktree. Migrations `0005`–`0009` below are proposed unused numbers at planning time; check the ledger at implementation start and resolve conflicts without renumbering applied migrations.

| Files | Responsibility |
|---|---|
| `rust/src/webhook_admin.rs`, `rust/tests/webhook_admin.rs`, `rust/migrations/0005_webhook_endpoint_lifecycle.sql` | Endpoint lifecycle and secret rotation |
| `rust/src/routing.rs`, `rust/tests/routing.rs`, `rust/migrations/0006_delivery_targets.sql` | Target/sink model, routing rules and fan-out |
| `rust/src/callbacks/{mod.rs,config.rs,signing.rs,transport.rs,worker.rs}`, `rust/tests/{callback_security,callbacks}.rs`, `rust/migrations/0007_callbacks.sql` | Encrypted keys, safe egress, exact signatures and delivery worker |
| `rust/migrations/0008_callback_attempts.sql` | Callback worker leases/attempt identity, separate from agent identity |
| `rust/src/replay.rs`, `rust/tests/replay.rs`, `rust/migrations/0009_idempotent_replay.sql` | DLQ-only single/batch replay |
| `contracts/webhooks/v1/{schema.json,fixtures.json,signing-fixtures.json,openapi.json}` | Additive v1 contracts and independent signing fixtures |
| `sdks/remake/node/src/callbacks.ts`, `sdks/remake/go/callbacks.go` and matching tests | Verifier helpers and management client methods |
| `web/remake-admin/src/Webhooks.tsx`, `web/remake-admin/tests/webhooks.spec.ts` | Ingress/callback configuration, tests, history and replay |
| `scripts/webhook-acceptance.sh`, `tests/webhooks/` | Independent receiver and two-replica acceptance evidence |

Shared types in `routing.rs`: `Sink = Agent | Callback`, `Target{target_id:Uuid,app_id:Uuid,sink:Sink}`, `RuleInput{source_app_id:Option<Uuid>,event_type:String,target_app_id:Uuid,sink:Sink,enabled:bool}`, `DispatchReceipt{event_id:Uuid,primary:Accepted,targets:Vec<TargetReceipt>}` and `TargetReceipt{target_id:Uuid,delivery_id:Uuid,generation:i32}`. Existing `Accepted` remains unchanged. Routing rules apply only within the authenticated workspace. Endpoint primary agent delivery remains the sole response source. Add `GET /api/v1/events/{event_id}/deliveries` for authorized fan-out inspection without changing old status responses.

Execution: land the crate-private authentication helper from F2 of the [foundation plan](2026-10-31-relayhub-centrifugo-foundation.md) before new management routes. W1 and W3 can then be independently developed after shared contracts are frozen; W2 follows W1, W4 joins W2/W3, W5 follows W2/W4, W6 verifies all. Serialize `host.rs`, migration registration, `dashboard.rs` and SDK/dashboard integration edits through the main agent; do not let multiple subagents overwrite them.

### Task W1: Complete endpoint lifecycle and freeze ingress behavior

**Files:** Create `rust/src/webhook_admin.rs`, `rust/tests/webhook_admin.rs`, migration `0005` and webhook schema/fixtures; modify `rust/src/{lib.rs,host.rs,webhooks.rs,dashboard.rs}`, `rust/tests/webhooks.rs` only for targeted regression coverage.

**Interfaces:** `WebhookAdmin::create(&self,p:&Principal,app:Uuid,input:EndpointInput)->Result<EndpointCreated,WebhookError>`, `update(&self,p:&Principal,id:Uuid,revision:i64,input:EndpointUpdate)->Result<EndpointView,WebhookError>`, `rotate_secret(&self,p:&Principal,id:Uuid,revision:i64)->Result<EndpointSecret,WebhookError>`, `archive(&self,p:&Principal,id:Uuid,revision:i64)->Result<(),WebhookError>`. `EndpointInput{policy:EndpointPolicy,auth:Public|Bearer,event_type:String}`; views contain ID/app/policy/auth mode/enabled/revision, never a secret. Created/rotated bearer returns a random secret once. Base routes `/api/v1/apps/{app_id}/webhook-endpoints`, item `/api/v1/webhook-endpoints/{id}`, `/rotate-secret`; owner/admin only, with existing cookie/CSRF or scoped management authentication.

- [ ] Write `endpoint_lifecycle_preserves_accepted_work`: create bearer endpoint, accept binary request, rotate secret, assert old bearer rejects new requests while accepted work still delivers; disable/archive rejects new ingress without deleting history; stale revision returns conflict. Re-run sync/offline/timeout tests at exact v1 boundaries and assert duplicate safe headers survive. Fixture includes mixed-case `Authorization`, `Cookie`, `Connection: X-Private` and `X-Private`, and asserts all are absent after filtering for HTTP ingress and SDK-published envelopes. Cross-workspace mutation is forbidden and secret never appears in list/audit/log output.
- [ ] Run `cargo test --manifest-path rust/Cargo.toml --test webhook_admin --test webhooks`; expect new lifecycle tests FAIL before implementation, existing ingress tests remain the baseline.
- [ ] Implement lifecycle state/revision, hash-only bearer storage and tombstones. Make ingress verify enabled state in the same acceptance transaction as event insertion, preventing a disable/check race. Preserve existing dashboard routes as adapters to the same service. No provider-specific signature guessing. Add exact create/update/list/error contracts and examples with synthetic credentials.
- [ ] Run both test targets plus `--test connector --test contracts`; expect PASS, with response regressions covered by the existing `webhooks` target. Verify response/payload limits at exactly 1 MiB and one byte over, and ingress `202` only after commit during broker outages.
- [ ] Commit only W1 files/hunks: `git commit -m "feat: complete webhook endpoint lifecycle"`.

### Task W2: Add immutable delivery targets and workspace routing

**Files:** Create `routing.rs`, `rust/tests/routing.rs`, migration `0006`; modify `rust/src/{events,delivery,outbox,gateway,responses,webhooks,host}.rs`, quota/migration tests, webhook contracts. Preserve existing migration files; schema changes belong in the new migration.

**Interfaces:** `Routing::resolve(&self,tx:&mut Transaction<'_,Postgres>,workspace:Uuid,source_app:Uuid,event_type:&str,primary_app:Uuid)->Result<Vec<Target>,AcceptError>`; `Events::accept_routed(&self,p:&Principal,input:EventInput,idempotency_key:&str)->Result<DispatchReceipt,AcceptError>`. Existing `accept_event` delegates and returns `.primary`. CRUD rules at `/api/v1/routing-rules` and `/{id}`, owner/admin only; source app/type are taken from trusted endpoint/configuration, not client-supplied workspace fields.

- [ ] Write `routing_is_atomic_and_target_scoped`: one source with two targets creates one event and independent target deliveries; overlapping rules deduplicate targets; retries return the same target set even after rules change. At workspace quota boundary all acceptance succeeds or none does. Cross-workspace target and 33rd target reject before commit. Replay/settlement of one target cannot alter another; a routed secondary agent response cannot settle the primary synchronous request.
- [ ] Run `cargo test --manifest-path rust/Cargo.toml --test routing --test durability`; expect routing cases FAIL against the single-target schema.
- [ ] Add `delivery_targets` with immutable workspace/event/target-app/sink identity and event `primary_target_id`. Backfill each existing event with one primary agent target. Replace uniqueness `(event_id,generation)` with `(target_id,generation)` and active-generation guards per target; preserve source event ownership while target app controls receiving. Update FKs and quota trigger to fetch event payload by workspace/event, separately validating target app in the same workspace. Filter gateway claims/outbox subjects by agent sink; callback dispatch uses its own subject/worker. Scope status access explicitly to source publisher, target receiver's own delivery, or workspace owner. Route snapshots/target creation occur in the acceptance transaction; no recomputation on retry/replay. Keep single-target sync response selection explicit. Endpoint policy `expire_pending` affects primary work only, as the design specifies.
- [ ] Run routing plus `--test durability --test delivery --test recovery --test webhooks --test host --test contracts`; expect PASS on an empty schema and a restored pre-change database. Check quota totals after each target settles/expires/replays and migration backfill preserves event IDs, payloads and old receipts. Compare all existing public/durable fixtures unchanged.
- [ ] Commit `git commit -m "feat: route durable webhook events to isolated targets"`. Callback routes stay unavailable until W4 is enabled; no partial advertised support.

### Task W3: Implement callback keys, signatures and safe HTTP transport

**Files:** Create `callbacks/{mod.rs,config.rs,signing.rs,transport.rs}`, `rust/tests/callback_security.rs`, migration `0007`, `contracts/webhooks/v1/signing-fixtures.json`; modify dependency lock/manifests only for maintained encryption/crypto libraries actually needed.

**Interfaces:** `CallbackConfigInput{url:String,enabled:bool}` and revisioned owner/admin routes `/api/v1/apps/{app_id}/callback`, `/api/v1/apps/{app_id}/callback/rotate-secret`, `/api/v1/apps/{app_id}/callback/retire-key/{key_id}`. One callback config per target app, enforced by a database unique constraint. `sign(secret:&[u8],timestamp:i64,request_target:&str,raw_body:&[u8])->String`; `CallbackTransport::send(&self,target:&PinnedTarget,request:SignedCallback)->Result<CallbackResponse,CallbackTransportError>`. `PinnedTarget` carries validated HTTPS URL, TLS hostname and approved resolved IPs; `SignedCallback` contains immutable bytes and generated headers. `CallbackResponse{status:u16,retry_after:Option<String>}` carries no arbitrary headers/body to audit. Config key encryption has explicit key ID/nonce/ciphertext and authenticated app/workspace identity.

- [ ] Write `callback_signature_and_egress_boundary`: use fixtures with non-ASCII text, binary original data, empty body, escaped path and reordered query; assert exact signature bytes and tamper failure. Reject redirect, metadata IP, IPv4-mapped IPv6, mixed public/private DNS answers and rebind after validation; test pinned IP uses original TLS hostname. Stored key ciphertext decrypts only with the correct operator key and tenant context. Logs/errors omit secret and URL query. Rotation preserves the accepted delivery's key version; retiring it prevents a new send.
- [ ] Run `cargo test --manifest-path rust/Cargo.toml --test callback_security`; expect FAIL for missing callback security implementation.
- [ ] Implement versioned callback config and one-time key presentation using maintained authenticated-encryption/HMAC libraries; load the operator encryption key from a secret file and fail startup when missing for enabled callbacks. Implement the design's exact HMAC canonical string, redirect/proxy denial, per-attempt DNS validation/pinning, 10-second timeout and 1 MiB response cap. Keep production URL policy independent of connector's explicitly local/LAN policy. Return stable safe error codes rather than reqwest errors containing raw URLs.
- [ ] Run the test target and cross-check fixtures using the existing Go `VerifyCallbackSignature` primitive and an independent Node crypto calculation; expect PASS. Use a controlled resolver/transport for private-address cases, not requests to actual metadata endpoints. Verify disabled callback mode requires no new secrets.
- [ ] Commit `git commit -m "feat: secure and sign outbound webhook requests"`.

### Task W4: Deliver callbacks durably with persisted attempts

**Files:** Create `callbacks/worker.rs`, `rust/tests/callbacks.rs`, `rust/migrations/0008_callback_attempts.sql`; modify `rust/src/{host,delivery,outbox}.rs` and webhook contract/status adapters. Add `tests/webhooks/receiver.mjs`, `scripts/webhook-acceptance.sh` with disposable service setup reusing Rust test conventions.

**Interfaces:** `CallbackWorker::run(&self,shutdown:CancellationToken)->Result<(),CallbackError>`, `classify(status:Option<u16>,transport_error:bool,retry_after:Option<&str>,attempt:u8,now:DateTime<Utc>)->CallbackDecision`; `CallbackDecision = Succeeded | RetryAt(DateTime<Utc>) | DeadLetter{reason:SafeReason}`. `Deliveries` gains sink-specific claim/settle methods using the existing lease token type, with callback worker identity distinct from an authenticated agent. A worker may not claim an agent delivery.

- [ ] Write `callback_restart_retry_and_fencing`: classify `2xx`, redirects, `400/401`, `408/425/429`, `5xx` and transport timeout exactly; attempt five becomes DLQ. Assert bounded `Retry-After`, immutable body/key snapshot, fresh timestamp per attempt and idempotent receiver effect. Crash after remote success before local settlement, restart and assert possible resend retains event/target identity; stale worker cannot settle a successor. Stop broker/Redis and show committed work remains recoverable from PostgreSQL.
- [ ] Run `cargo test --manifest-path rust/Cargo.toml --test callbacks`; expect FAIL for missing worker.
- [ ] Implement callback notifications through a sink-specific durable outbox subject, PostgreSQL claims/leases and recovery sweeps. Generalize attempts to an explicit worker kind/ID rather than pretending a callback worker is an end-user agent; preserve agent identity requirements for agent attempts. Persist exact body/config/key snapshots per generation and safe attempt outcomes before broker ACK. Apply five-attempt v1 retry policy, bounded worker concurrency of 16 per process and transactional per-target claim guards. Check enabled/retired key policy before each send: disabled configs pause unclaimed work without consuming an attempt; retired keys transition unclaimed work to DLQ with `key_retired`. Retirement cannot undo already emitted effects. Retention expiry remains terminal and visible.
- [ ] Run callback tests and `scripts/webhook-acceptance.sh --suite callbacks`; expect PASS with two replicas and independent receiver signature/effect verification. Re-run existing durable/realtime suites; callback workers must never consume agent messages or change ephemeral realtime behavior.
- [ ] Commit `git commit -m "feat: deliver signed callbacks with durable retries"`.

### Task W5: Make DLQ replay scoped, fenced and idempotent

**Files:** Create `rust/src/replay.rs`, `rust/tests/replay.rs`, migration `0009`; modify `rust/src/{delivery,dashboard,lib}.rs` and webhook/OpenAPI contracts. Update the old test permitting replay of succeeded deliveries to assert the reviewed DLQ-only behavior.

**Interfaces:** `Replay::batch(&self,p:&Principal,request:ReplayRequest)->Result<ReplayReceipt,ReplayError>` where `ReplayRequest{request_id:Uuid,delivery_ids:Vec<Uuid>,callback_config_revisions:HashMap<Uuid,i64>}` and `ReplayReceipt{request_id:Uuid,deliveries:Vec<TargetReceipt>}`. Revision map keys are target IDs; omitted map is empty. New `POST /api/v1/deliveries/replay` takes that JSON object. Single replay UI/API delegates with a one-ID list; preserve the existing route with a newly required `Idempotency-Key` UUID header and document its behavior change. Existing internal `replay_delivery` cannot bypass these checks.

- [ ] Write `replay_is_atomic_and_idempotent`: same request/selection/revision map returns exactly the same new delivery IDs and creates one audit entry; changed content under the same ID conflicts. Reject succeeded/cancelled/expired, unretained, cross-workspace and 101 IDs. One invalid member rejects the entire batch. Concurrent requests for the same DLQ target allow one active generation; old callback/agent leases cannot settle it. A retired key blocks plain replay; explicit enabled replacement config revision in the same target app succeeds and preserves the event/target identity. Other-app replacement revisions are forbidden.
- [ ] Run `cargo test --manifest-path rust/Cargo.toml --test replay`; expect FAIL against missing request records and permissive replay.
- [ ] Implement replay request/digest/result records under workspace+actor+request ID, canonicalize selection/revision maps, lock selected targets in stable order and atomically create per-target generations/outbox/quota/audit. Validate replacement configs under the same transaction; pin the selected config/key on the new generation and record the explicit reconfiguration in audit. Deduplicate completed replay requests before checking the now-changed delivery state. Retain replay identity/results with the event for seven days. Never call the routing resolver or republish the original event. Align callback and agent replay with the same service and safe timeline output.
- [ ] Run replay, delivery, callback and two-replica concurrency tests; expect PASS. Test a whole batch at quota boundary rolls back without partial new generations or audit success. Document the intentional old-test/contract correction in the release notes.
- [ ] Commit `git commit -m "fix: enforce idempotent DLQ-only webhook replay"`.

### Task W6: Ship SDK helpers, dashboard flows and verified product examples

**Files:** Create `sdks/remake/node/src/callbacks.ts`, `sdks/remake/node/test/callbacks.test.ts`, `sdks/remake/go/callbacks.go`, `sdks/remake/go/callbacks_test.go`; create `web/remake-admin/src/Webhooks.tsx`, `web/remake-admin/tests/webhooks.spec.ts`; modify `web/remake-admin/src/{api.ts,Workspace.tsx,Deliveries.tsx}`, SDK manifests/exports and webhook acceptance harness. Add callback/inbound examples under `examples/remake/` consumed by D3 of the [docs plan](2026-10-31-relayhub-product-docs.md).

**Interfaces:** Node `verifyCallbackSignature({secret,timestamp,requestTarget,body,signature,now,maxSkewSeconds=300}):boolean`; Go `VerifyCallbackSignature(secret,timestamp,requestTarget string,body []byte,signature string,now time.Time,maxSkew time.Duration)bool`. Request body is the original received HTTP bytes, not parsed/re-serialized JSON. SDK management methods mirror W1/W2/W3/W5 types; browser entry exports no server signing secret/helper. Dashboard groups Incoming endpoints, Outgoing callbacks, Routing and Delivery history.

- [ ] Write SDK fixtures proving Rust→Node/Go verification, timestamp boundary ±300 seconds, body/query tamper and binary request preservation. Browser test configures an inbound endpoint and outbound callback, sends a normal durable test with stable request ID, observes two target outcomes, drives a failure to DLQ and replays once despite double submission. Assert one-time secrets, no source credentials in browser storage and no URL queries/raw headers in timeline views.
- [ ] Run SDK tests, `npm --prefix web/remake-admin test -- webhooks.spec.ts`, and `scripts/webhook-acceptance.sh --suite all`; expect new UI/helper cases FAIL before integration.
- [ ] Implement helpers with standard crypto/constant-time comparisons and strict malformed input rejection. Add management UI and bounded attempt/timeline views with cursor pagination (default 50, maximum 100). Callback configuration/test actions use same-origin cookie/CSRF authentication and owner permissions; test delivery uses normal acceptance/retry/audit, never an unaudited special sender. Route forms and sync mode explain primary response vs asynchronous additional targets. Link product use cases and verified downloads; update only owned API/contract sections, preserving unrelated OpenAPI work.
- [ ] Run full webhook acceptance, SDK builds/tests, browser typecheck/build/Playwright and existing Rust legacy gates. Expect PASS with recorded source versions and no missing scenarios. Restore a pre-change backup, apply additive migrations in an isolated cluster, run acceptance, then rehearse rollback by disabling new producers/workers and preserving target data; old binaries must not be pointed at an incompatible fan-out schema without a reviewed restore plan. Add webhook evidence to the release manifest and docs capability catalog. Create vault `docs/services/relayhub-webhooks.md` with the operator-key secret file/1Password mapping, database/key backup and restore procedure, exact revision and prepared rollout state; no secret values or production key creation during tests.
- [ ] Commit/push feature branches to available owned GitHub/GitLab remotes: `git commit -m "feat: expose complete webhook integration workflows"`. Present migration/backup/rollback and rollout evidence for production review; do not merge main or mutate production automatically.

## Handoff and verification record

Source audit found existing ingress/agent behavior and missing outbound parity; no implementation or tests were run while writing this plan. Main-agent self-review maps all webhook design requirements to W1–W6 and preserves the separate paused Rust task. After plan review, use the previously requested subagent method; docs work may proceed in parallel against frozen contracts with explicit preview labels.
