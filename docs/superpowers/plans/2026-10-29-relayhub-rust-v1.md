# RelayHub Rust v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a workspace-isolated Rust RelayHub with durable socket agents, configurable webhook tunnels, realtime, CLI, Node and Go SDKs.

**Architecture:** Retain PostgreSQL for authoritative acceptance/control state, JetStream for durable transport and Redis for ephemeral coordination. Implement alongside the Go deployment with new contracts and isolated staging resources.

**Tech Stack:** Rust/Tokio/Axum/SQLx/async-nats/Redis; PostgreSQL; NATS JetStream; React/TypeScript; Node.js and Go SDKs. Dependency versions must be selected from supported official releases and locked during Task 1.

**Spec:** [Design baseline](../specs/2026-10-29-relayhub-rust-v1-design.md). User requested planning directly after scope discussion; detailed defaults require review before implementation.

## Global Constraints

- Source paths below are relative to `/home/dungxbuif/workspace/projects/RelayHub`; planning docs stay in homelab.
- Rust replaces server/CLI; retain PostgreSQL + NATS JetStream + Redis. API/SDK backwards compatibility is not required.
- Only administrators create accounts; every user receives a separate workspace.
- Copy all numerical limits and mode semantics from the spec's “Proposed precise defaults” without changing them implicitly.
- Delivery is at least once; do not promise exactly once or cancellation of already-claimed work.
- No production replacement, old-code deletion, main merge or live credential export during implementation.
- No full TCP tunnel, general website proxy, remote functions, public signup or billing in this v1.
- SDK source for the remake is separate from existing SDKs; preserve existing users during development.

## Review Focus

- Cross-workspace guessed IDs and forged socket fields must never authorize access: Tasks 2, 6, 10.
- Disconnect after a side effect but before ACK must not imply exactly-once behavior: Tasks 4, 7–9.
- Late sync responses must not satisfy another HTTP request: Task 5.
- Local tunnel targets and redirects must not enable arbitrary internal access: Task 7.
- Concurrent admissions, restarts and broker duplicates must not lose accepted work or bypass quotas: Tasks 3, 4, 11.

## Structure and sequencing

This is one integration product with separately testable work packages, not independent rewrites. Follow 1→2→3→4→5. Task 6 follows 2/4; Tasks 7–9 consume the frozen protocol and gateway; Task 10 consumes control APIs; Task 11 integrates all. SDKs may be implemented independently once protocol fixtures are frozen. Each task lists its owned files; do not modify the old Go backend or SDKs to scaffold the remake.

Common Rust integration harness: Task 1 creates `rust/tests/support/mod.rs` with disposable service connections and per-test workspace/subject isolation. Tests use real stores, never production URLs. Every test run must report executed tests, not an all-skipped success. Test inventories below are named assertions to implement, not existing test results.

---

### Task 1: Contracts and Rust acceptance harness

**Files:** Create `rust/Cargo.toml`, `rust/src/lib.rs`, `rust/src/protocol.rs`, `contracts/v1/schema.json`, `contracts/v1/fixtures.json`, `rust/tests/contracts.rs`.

**Interfaces:** parse_frame(bytes: &[u8]) -> Result<Frame, ProtocolError>; Frame variants Hello, Delivery, Ack, Response, Realtime, Heartbeat with request_id, event_id, attempt_token where applicable. Consumes the spec and Task 1 protocol types. Protocol changes require updating shared fixtures and both SDK tests together.

- [ ] **Step 1: Add failing tests** named `golden_frames_roundtrip`, `reject_unknown_version`, `reject_body_over_1048576`, `preserve_binary_and_duplicate_headers`. Each name is the required observable assertion; use exact limits and return codes from the spec, and assert persistent state as well as the API result.
- [ ] **Step 2: Verify red:** run `cargo test --manifest-path rust/Cargo.toml --test contracts`; confirm failures are missing/unimplemented behavior, not unavailable infrastructure. For a new package first add the minimal manifest/test runner needed to execute its tests.
- [ ] **Step 3: Implement the declared interfaces:** Define serde types and JSON fixtures for every variant, authenticated identity, EventInput, Accepted, EndpointPolicy, DeliveryLease and HttpResponse. Lock Rust dependencies using Tokio, Axum, SQLx, async-nats, Redis client, serde, tracing and reqwest; verify supported compiler/library versions at execution. Add disposable integration Compose with PostgreSQL/NATS/Redis, separate namespaces and no production credentials.
- [ ] **Step 4: Verify green:** run `cargo test --manifest-path rust/Cargo.toml --test contracts`; all named assertions must execute and pass. Preserve fixture compatibility from Task 1.
- [ ] **Step 5: Commit** only this task's listed files and necessary lockfiles with message `feat: contracts and rust acceptance harness`; review the staged diff for secrets and unrelated changes first.

### Task 2: Identity and workspace boundary

**Files:** Create `rust/src/identity.rs`, `rust/migrations/0001_identity.sql`, `rust/tests/identity.rs`.

**Interfaces:** authenticate(token: &str) -> Result<Principal, AuthError>; authorize(principal: &Principal, workspace_id: Uuid, action: Action) -> Result<(), AuthError>. Consumes the spec and Task 1 protocol types. Protocol changes require updating shared fixtures and both SDK tests together.

- [ ] **Step 1: Add failing tests** named `cross_workspace_returns_403`, `disabled_key_disconnects_socket`, `password_setup_token_is_single_use`, `expired_setup_token_rejected`, `csrf_blocks_cookie_write`. Each name is the required observable assertion; use exact limits and return codes from the spec, and assert persistent state as well as the API result.
- [ ] **Step 2: Verify red:** run `cargo test --manifest-path rust/Cargo.toml --test identity`; confirm failures are missing/unimplemented behavior, not unavailable infrastructure. For a new package first add the minimal manifest/test runner needed to execute its tests.
- [ ] **Step 3: Implement the declared interfaces:** Implement admin-only account provisioning, atomic user/workspace creation, hashed one-time setup tokens, password hashing and revocable sessions. Define admin, owner, app and agent principals; credential scopes cannot be escalated by request fields. Create /api/v1/admin/users, /session, /workspaces/{id}/apps and /credentials routes with OpenAPI contracts.
- [ ] **Step 4: Verify green:** run `cargo test --manifest-path rust/Cargo.toml --test identity`; all named assertions must execute and pass. Preserve fixture compatibility from Task 1.
- [ ] **Step 5: Commit** only this task's listed files and necessary lockfiles with message `feat: identity and workspace boundary`; review the staged diff for secrets and unrelated changes first.

### Task 3: Durable acceptance and outbox recovery

**Files:** Create `rust/src/events.rs`, `rust/src/outbox.rs`, `rust/migrations/0002_events.sql`, `rust/tests/durability.rs`.

**Interfaces:** accept_event(principal: &Principal, input: EventInput, idempotency_key: &str) -> Result<Accepted, AcceptError>; dispatch_outbox(batch_size: u32) -> Result<u32, DispatchError>. Consumes the spec and Task 1 protocol types, plus earlier authenticated principal and acceptance contracts. Protocol changes require updating shared fixtures and both SDK tests together.

- [ ] **Step 1: Add failing tests** named `commit_survives_broker_outage`, `publish_crash_deduplicates`, `changed_body_same_key_conflicts`, `concurrent_limit_returns_429`, `cross_workspace_key_not_shared`. Each name is the required observable assertion; use exact limits and return codes from the spec, and assert persistent state as well as the API result.
- [ ] **Step 2: Verify red:** run `cargo test --manifest-path rust/Cargo.toml --test durability`; confirm failures are missing/unimplemented behavior, not unavailable infrastructure. For a new package first add the minimal manifest/test runner needed to execute its tests.
- [ ] **Step 3: Implement the declared interfaces:** Create events/deliveries/outbox and quota accounting in PostgreSQL. Idempotency keys are workspace/app scoped; same key with different canonical payload returns 409. Enforce byte/count limits in acceptance transaction. Publish stable delivery ID to workspace-scoped JetStream subjects; broker PubAck precedes outbox mark. Run outbox and expiry worker loops; release quota on terminal delivery.
- [ ] **Step 4: Verify green:** run `cargo test --manifest-path rust/Cargo.toml --test durability`; all named assertions must execute and pass. Preserve fixture compatibility from Task 1.
- [ ] **Step 5: Commit** only this task's listed files and necessary lockfiles with message `feat: durable acceptance and outbox recovery`; review the staged diff for secrets and unrelated changes first.

### Task 4: Socket delivery, leases and offline replay

**Files:** Create `rust/src/gateway.rs`, `rust/src/delivery.rs`, `rust/src/presence.rs`, `rust/tests/delivery.rs`.

**Interfaces:** claim_delivery(agent: &Principal, delivery_id: Uuid) -> Result<DeliveryLease, ClaimError>; settle_delivery(agent: &Principal, lease: DeliveryLease, result: ProcessingResult) -> Result<(), SettleError>. Consumes the spec and Task 1 protocol types, plus earlier authenticated principal and acceptance contracts. Protocol changes require updating shared fixtures and both SDK tests together.

- [ ] **Step 1: Add failing tests** named `offline_wait_does_not_consume_attempt`, `reconnect_receives_pending`, `stale_ack_rejected`, `two_gateways_single_claim`, `redis_loss_preserves_event`, `retry_exhaustion_enters_dlq`, `restart_after_db_settle_before_broker_ack`. Each name is the required observable assertion; use exact limits and return codes from the spec, and assert persistent state as well as the API result.
- [ ] **Step 2: Verify red:** run `cargo test --manifest-path rust/Cargo.toml --test delivery`; confirm failures are missing/unimplemented behavior, not unavailable infrastructure. For a new package first add the minimal manifest/test runner needed to execute its tests.
- [ ] **Step 3: Implement the declared interfaces:** Use Redis expiring presence/ownership and NATS to route to owning gateway. PostgreSQL compare-and-set gates fenced attempts. Apply spec lease, heartbeat, attempt, in-flight and retention limits. Persist success before JetStream ACK; reconcile already-terminal duplicates. Expose authorized delivery read and replay routes; replay uses a new generation with audit record.
- [ ] **Step 4: Verify green:** run `cargo test --manifest-path rust/Cargo.toml --test delivery`; all named assertions must execute and pass. Preserve fixture compatibility from Task 1.
- [ ] **Step 5: Commit** only this task's listed files and necessary lockfiles with message `feat: socket delivery, leases and offline replay`; review the staged diff for secrets and unrelated changes first.

### Task 5: Configurable HTTP webhook tunnel

**Files:** Create `rust/src/webhooks.rs`, `rust/src/responses.rs`, `rust/migrations/0003_endpoints.sql`, `rust/tests/webhooks.rs`.

**Interfaces:** receive_webhook(endpoint_id: Uuid, request: HttpRequest) -> Result<HttpResponse, WebhookError>; complete_response(agent: &Principal, lease: DeliveryLease, response: HttpResponse) -> Result<(), ResponseError>. Consumes the spec and Task 1 protocol types, plus earlier authenticated principal and acceptance contracts. Protocol changes require updating shared fixtures and both SDK tests together.

- [ ] **Step 1: Add failing tests** named `async_returns_202_after_commit`, `sync_online_returns_app_response`, `offline_queue_202`, `offline_reject_503_no_enqueue`, `timeout_continue_202`, `expire_pending_504`, `late_response_cannot_answer_new_request`, `invalid_ingress_secret_rejected`. Each name is the required observable assertion; use exact limits and return codes from the spec, and assert persistent state as well as the API result.
- [ ] **Step 2: Verify red:** run `cargo test --manifest-path rust/Cargo.toml --test webhooks`; confirm failures are missing/unimplemented behavior, not unavailable infrastructure. For a new package first add the minimal manifest/test runner needed to execute its tests.
- [ ] **Step 3: Implement the declared interfaces:** Create endpoint policies and public /hooks/{endpoint_id} ingress. Atomically decide acceptance/offline policy using bounded presence evidence, then tolerate disconnect races through timeout behavior. Correlate responses across gateways using Redis, with authoritative result/state in PostgreSQL. Do not resubmit sync work merely because HTTP caller disconnected. Add event status endpoint scoped to owner/app.
- [ ] **Step 4: Verify green:** run `cargo test --manifest-path rust/Cargo.toml --test webhooks`; all named assertions must execute and pass. Preserve fixture compatibility from Task 1.
- [ ] **Step 5: Commit** only this task's listed files and necessary lockfiles with message `feat: configurable http webhook tunnel`; review the staged diff for secrets and unrelated changes first.

### Task 6: Realtime without durable guarantees

**Files:** Create `rust/src/realtime.rs`, `rust/tests/realtime.rs`.

**Interfaces:** publish_realtime(principal: &Principal, channel: &str, payload: &[u8]) -> Result<PublishReceipt, RealtimeError>. Consumes the spec and Task 1 protocol types, plus earlier authenticated principal and acceptance contracts. Protocol changes require updating shared fixtures and both SDK tests together.

- [ ] **Step 1: Add failing tests** named `cross_workspace_subscribe_denied`, `offline_publish_has_zero_recipients`, `no_replay_after_reconnect`, `two_gateway_fanout`, `slow_reader_is_bounded`. Each name is the required observable assertion; use exact limits and return codes from the spec, and assert persistent state as well as the API result.
- [ ] **Step 2: Verify red:** run `cargo test --manifest-path rust/Cargo.toml --test realtime`; confirm failures are missing/unimplemented behavior, not unavailable infrastructure. For a new package first add the minimal manifest/test runner needed to execute its tests.
- [ ] **Step 3: Implement the declared interfaces:** Add scoped subscribe/unsubscribe and publish frames through Core NATS. Redis maintains ephemeral ownership, not message durability. Per-connection outbound buffer 64 frames; disconnect slow readers with explicit reason. Return accepted routing receipt and best-effort observed subscriber count, never claim processing ACK. Reject payloads above spec limit.
- [ ] **Step 4: Verify green:** run `cargo test --manifest-path rust/Cargo.toml --test realtime`; all named assertions must execute and pass. Preserve fixture compatibility from Task 1.
- [ ] **Step 5: Commit** only this task's listed files and necessary lockfiles with message `feat: realtime without durable guarantees`; review the staged diff for secrets and unrelated changes first.

### Task 7: Rust CLI connector

**Files:** Create `rust/src/bin/relayhub.rs`, `rust/src/connector.rs`, `rust/tests/connector.rs`, `deploy/relayhub-agent.example.toml`.

**Interfaces:** run_connector(config: ConnectorConfig) -> Result<(), ConnectorError>; ConnectorConfig contains server_url, credential_file, endpoint_targets, max_in_flight. Consumes the spec and Task 1 protocol types, plus earlier authenticated principal and acceptance contracts. Protocol changes require updating shared fixtures and both SDK tests together.

- [ ] **Step 1: Add failing tests** named `local_http_receives_request`, `remote_target_override_rejected`, `redirect_not_followed`, `metadata_target_rejected`, `secret_not_logged`, `reconnect_replays_unacked`, `sigterm_drains`. Each name is the required observable assertion; use exact limits and return codes from the spec, and assert persistent state as well as the API result.
- [ ] **Step 2: Verify red:** run `cargo test --manifest-path rust/Cargo.toml --test connector`; confirm failures are missing/unimplemented behavior, not unavailable infrastructure. For a new package first add the minimal manifest/test runner needed to execute its tests.
- [ ] **Step 3: Implement the declared interfaces:** Implement relayhub connect --config <path> and relayhub version. Read token from protected credential file. Validate target mapping locally; apply header/body constraints and local HTTP timeout. Serialize success/response only after local handler completes. Shutdown stops new claims, allows 30-second drain then exits leaving unacked work recoverable.
- [ ] **Step 4: Verify green:** run `cargo test --manifest-path rust/Cargo.toml --test connector`; all named assertions must execute and pass. Preserve fixture compatibility from Task 1.
- [ ] **Step 5: Commit** only this task's listed files and necessary lockfiles with message `feat: rust cli connector`; review the staged diff for secrets and unrelated changes first.

### Task 8: Node.js SDK

**Files:** Create `sdks/remake/node/package.json`, `sdks/remake/node/src/client.ts`, `sdks/remake/node/src/agent.ts`, `sdks/remake/node/test/contracts.test.ts`, `sdks/remake/node/test/acceptance.test.ts`.

**Interfaces:** RelayHub.publish(input: EventInput, idempotencyKey: string): Promise<Accepted>; RelayHub.connectAgent(handler: (delivery: Delivery) => Promise<ProcessingResult>): Promise<AgentHandle>; AgentHandle.close(): Promise<void>. Consumes the spec and Task 1 protocol types, plus earlier authenticated principal and acceptance contracts. Protocol changes require updating shared fixtures and both SDK tests together.

- [ ] **Step 1: Add failing tests** named `golden_frames_match`, `handler_success_acks`, `thrown_handler_nacks`, `reconnect_redelivers_same_event_id`, `shutdown_drains`, `realtime_subscription_scoped`. Each name is the required observable assertion; use exact limits and return codes from the spec, and assert persistent state as well as the API result.
- [ ] **Step 2: Verify red:** run `npm --prefix sdks/remake/node test`; confirm failures are missing/unimplemented behavior, not unavailable infrastructure. For a new package first add the minimal manifest/test runner needed to execute its tests.
- [ ] **Step 3: Implement the declared interfaces:** Implement Node/TypeScript exports, backend credentials only, publish and agent lifecycle, realtime subscription/publish and typed sync responses. Reuse golden fixtures. Handler receives event_id and attempt metadata; document business idempotency requirement. Keep old sdks/typescript untouched; new package is explicitly experimental until cutover.
- [ ] **Step 4: Verify green:** run `npm --prefix sdks/remake/node test`; all named assertions must execute and pass. Preserve fixture compatibility from Task 1.
- [ ] **Step 5: Commit** only this task's listed files and necessary lockfiles with message `feat: node.js sdk`; review the staged diff for secrets and unrelated changes first.

### Task 9: Go SDK

**Files:** Create `sdks/remake/go/go.mod`, `sdks/remake/go/client.go`, `sdks/remake/go/agent.go`, `sdks/remake/go/acceptance_test.go`.

**Interfaces:** Client.Publish(ctx context.Context, input EventInput, key string) (Accepted, error); Client.RunAgent(ctx context.Context, handler func(context.Context, Delivery) (ProcessingResult, error)) error. Consumes the spec and Task 1 protocol types, plus earlier authenticated principal and acceptance contracts. Protocol changes require updating shared fixtures and both SDK tests together.

- [ ] **Step 1: Add failing tests** named `golden_frames_match`, `handler_success_acks`, `handler_error_retries`, `context_cancel_drains`, `reconnect_redelivers_same_event_id`, `race_free_subscription_close`. Each name is the required observable assertion; use exact limits and return codes from the spec, and assert persistent state as well as the API result.
- [ ] **Step 2: Verify red:** run `go -C sdks/remake/go test -race ./...`; confirm failures are missing/unimplemented behavior, not unavailable infrastructure. For a new package first add the minimal manifest/test runner needed to execute its tests.
- [ ] **Step 3: Implement the declared interfaces:** Match Node contracts and shared JSON fixtures, provide realtime APIs and context-aware shutdown. Keep existing sdks/go untouched. Run real acceptance suite against Rust endpoints and Go race detector.
- [ ] **Step 4: Verify green:** run `go -C sdks/remake/go test -race ./...`; all named assertions must execute and pass. Preserve fixture compatibility from Task 1.
- [ ] **Step 5: Commit** only this task's listed files and necessary lockfiles with message `feat: go sdk`; review the staged diff for secrets and unrelated changes first.

### Task 10: Workspace dashboard

**Files:** Create `web/remake-admin/package.json`, `web/remake-admin/src/App.tsx`, `web/remake-admin/src/api.ts`, `web/remake-admin/src/Workspace.tsx`, `web/remake-admin/src/Deliveries.tsx`, `web/remake-admin/tests/workspace.spec.ts`.

**Interfaces:** API client uses generated OpenAPI types; routes /login, /admin/users, /workspaces/{id}, /workspaces/{id}/deliveries. Consumes the spec and Task 1 protocol types, plus earlier authenticated principal and acceptance contracts. Protocol changes require updating shared fixtures and both SDK tests together.

- [ ] **Step 1: Add failing tests** named `user_cannot_open_other_workspace`, `admin_creates_user`, `configure_sync_offline_policy`, `replay_is_audited`, `offline_realtime_test_shows_zero`, `durable_test_moves_pending_to_ack`. Each name is the required observable assertion; use exact limits and return codes from the spec, and assert persistent state as well as the API result.
- [ ] **Step 2: Verify red:** run `npm --prefix web/remake-admin exec playwright test`; confirm failures are missing/unimplemented behavior, not unavailable infrastructure. For a new package first add the minimal manifest/test runner needed to execute its tests.
- [ ] **Step 3: Implement the declared interfaces:** Build separate frontend using existing admin React conventions. Add app/credential creation with one-time secret display, endpoint configuration, agent presence, cursor-paginated delivery timeline and confirmed replay. Expose separate realtime/durable test actions and render payload text safely. Never expose app keys in browser realtime tests; issue scoped expiring tokens.
- [ ] **Step 4: Verify green:** run `npm --prefix web/remake-admin exec playwright test`; all named assertions must execute and pass. Preserve fixture compatibility from Task 1.
- [ ] **Step 5: Commit** only this task's listed files and necessary lockfiles with message `feat: workspace dashboard`; review the staged diff for secrets and unrelated changes first.

### Task 11: Release rehearsal and migration handoff

**Files:** Create `deploy/remake/compose.yaml`, `deploy/remake/Dockerfile`, `scripts/remake-acceptance.sh`, `docs/operations/remake-cutover.md`, `rust/tests/recovery.rs`.

**Interfaces:** scripts/remake-acceptance.sh exits 0 only when Rust, CLI, Node, Go and dashboard acceptance pass against disposable services. Consumes the spec and Task 1 protocol types, plus earlier authenticated principal and acceptance contracts. Protocol changes require updating shared fixtures and both SDK tests together.

- [ ] **Step 1: Add failing tests** named `broker_restart_preserves_pending`, `redis_restart_reconnects`, `postgres_restore_recovers_outbox`, `gateway_kill_fences_old_ack`, `old_and_new_namespaces_isolated`. Each name is the required observable assertion; use exact limits and return codes from the spec, and assert persistent state as well as the API result.
- [ ] **Step 2: Verify red:** run `bash scripts/remake-acceptance.sh`; confirm failures are missing/unimplemented behavior, not unavailable infrastructure. For a new package first add the minimal manifest/test runner needed to execute its tests.
- [ ] **Step 3: Implement the declared interfaces:** Create staging artifacts with resource limits, health endpoints, graceful drain and redacted telemetry. Verify two-gateway behavior and restore. Use dedicated shared PostgreSQL DB/user with Databasus enrollment when separately executing staging provisioning. Document old-work drain, one-app migration, stop criteria and rollback without data deletion. Production cutover remains an explicit later action.
- [ ] **Step 4: Verify green:** run `bash scripts/remake-acceptance.sh`; all named assertions must execute and pass. Preserve fixture compatibility from Task 1.
- [ ] **Step 5: Commit** only this task's listed files and necessary lockfiles with message `feat: release rehearsal and migration handoff`; review the staged diff for secrets and unrelated changes first.

## Self-review and handoff

Coverage: identity/workspaces T2; acceptance/outbox T3; offline queue/ACK/DLQ T4; configurable tunnel T5/T7; realtime T6; SDKs T8/T9; dashboard/tests T10; recovery/backup/cutover T11. All five review-focus conditions have owning tests. API request/response schemas freeze in T1 and are consumed by all subsequent tasks.

Before execution review the spec's proposed defaults, confirm retained scope and execution method. Recommend subagent-driven execution with separate review gates because delivery fencing, multi-store recovery and workspace authorization are distinct failure boundaries. No implementation has been performed by creating this plan.

