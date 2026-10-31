# RelayHub v1 Host Integration and Drain Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the unused Rust remake a runnable v1 host with dashboard adapters and a complete graceful-drain contract.

**Architecture:** Reuse the existing Identity, Events, Outbox, Gateway, Webhooks, Realtime and Responses modules. Add one thin host composition and one server-to-agent Drain frame; the Gateway owns claim fencing and the host owns lifecycle/configuration.

**Tech Stack:** Rust 1.99, Axum 0.8, Tokio, SQLx/PostgreSQL, async-nats JetStream/Core NATS, Redis, WebSocket, Node SDK, Go SDK, Playwright.

**Spec:** `/home/dungxbuif/workspace/vaults/homelab/docs/superpowers/specs/2026-10-29-relayhub-v1-host-integration-design.md`, layered on the Rust v1 baseline design.

## Global Constraints

- Preserve at-least-once semantics and event-ID deduplication; never claim exactly once.
- Drain deadline is at most 30 seconds; no new claim after Drain is observed.
- Drain is a breaking v1 frame change; update Rust fixtures and both remake SDKs together.
- Workspace identity always comes from authenticated session/credential or scoped token, never request fields.
- Browser realtime uses a 60-second workspace/channel/publish-only token, never an app key.
- No production cutover, external secret, old SDK change or full TCP tunnel.

## Review Focus

- A Drain arriving between claim and send must roll back/unsettle only the un-emitted claim and never emit a new delivery: Gateway drain regression.
- An old ACK/Response after Drain or reconnect must remain fenced: delivery regression plus host acceptance.
- A browser token must not publish outside its workspace/channel or call durable routes: scoped-token host tests.
- A 403/CSRF failure must not leak workspace data or replay controls: dashboard browser regression.
- Shutdown must terminate all worker/socket tasks and exact disposable Compose resources: host acceptance/trap check.

---

### Task 1: Freeze Drain protocol

**Files:**
- Modify: `rust/src/protocol.rs`, `contracts/v1/schema.json`, `contracts/v1/fixtures.json`
- Test: `rust/tests/contracts.rs`

**Interfaces:** Produce `Frame::Drain { version: u16, request_id: Uuid, deadline_ms: u32 }` with validation 1–30,000 and canonical JSON. Update shared fixtures; reject unknown fields and invalid deadlines.

- [ ] Add red round-trip/invalid-boundary tests.
- [ ] Implement the enum and schema/fixture updates.
- [ ] Run locked contract tests and commit `feat: freeze v1 drain frame`.

### Task 2: Gateway drain lifecycle

**Files:**
- Modify: `rust/src/gateway.rs`, `rust/src/lib.rs`
- Test: `rust/tests/delivery.rs`

**Interfaces:** Gateway exposes `pub fn drain(&self, deadline: Duration) -> Result<(), ...>` and socket sessions subscribe to the broadcast. Drain sends the frame, stops `pending()` claims, allows outstanding ACK/Response/heartbeat, and closes when empty/deadline.

- [ ] Add red tests for no post-drain claim, active settle, stale fencing and deadline close.
- [ ] Implement broadcast/session state without changing lease SQL ownership.
- [ ] Run focused delivery, full Rust suite and scoped review; commit `feat: drain gateway sessions`.

### Task 3: SDK drain behavior

**Files:**
- Modify: `sdks/remake/node/src/client.ts`, `sdks/remake/node/src/agent.ts`, `sdks/remake/node/test/acceptance.test.ts`
- Modify: `sdks/remake/go/client.go`, `sdks/remake/go/agent.go`, `sdks/remake/go/acceptance_test.go`

**Interfaces:** Both decoders accept Drain. Agent loops stop new admission/reconnect, settle active handlers, and close by the advertised deadline. Existing local `close()` remains supported.

- [ ] Add red Node/Go tests for Drain during idle, queued and active work.
- [ ] Implement minimal state transitions; do not invent NACK or persistence.
- [ ] Run Node 14+ tests, Go race/vet and Rust adapter checks; commit `feat: drain remake sdk agents`.

### Task 4: Rust host composition and dashboard adapters

**Files:**
- Create: `rust/src/host.rs`, `rust/src/bin/relayhub-server.rs`
- Modify: `rust/src/lib.rs`, `rust/src/identity.rs`, `rust/src/events.rs`, `rust/src/gateway.rs`, `rust/src/webhooks.rs`, `rust/src/realtime.rs`, `rust/Cargo.toml`, `rust/Cargo.lock`
- Test: `rust/tests/host.rs`

**Interfaces:** `Host::from_env()`, `Host::migrate()`, `Host::router()`, `Host::shutdown()` compose existing modules. Add `POST /api/v1/events`, workspace endpoint/agent/delivery/replay/audit routes, and scoped realtime-token issue/validation. Merge gateway routing without the old auth-only socket route. Dispatch socket Response frames to `Responses::complete_response`.

- [ ] Add red host tests for authenticated publish, response completion, workspace 403, replay audit, scoped token boundaries and route collision absence.
- [ ] Implement configuration, migrations, worker tasks, auth/CSRF layer and bounded JSON bodies using existing module APIs.
- [ ] Run host tests and locked check; commit `feat: compose relayhub v1 host`.

### Task 5: Release integration

**Files:**
- Modify: `deploy/remake/compose.yaml`, `deploy/remake/Dockerfile`, `scripts/remake-acceptance.sh`, `docs/operations/remake-cutover.md`, `rust/tests/recovery.rs`
- Test: `rust/tests/recovery.rs` and dashboard/SDK suites

**Interfaces:** Staging artifacts run `relayhub-server`; acceptance must exercise real host routes and Drain, not only library mocks. Recovery tests retain existing names and add host publish/restore/drain assertions where needed.

- [ ] Add red acceptance assertions for live host, Response dispatch and graceful drain.
- [ ] Replace the current missing-host fail gate with real host startup and keep fail-closed cleanup/redaction.
- [ ] Run bounded full acceptance; update cutover criteria only when all gates pass; commit `feat: release host rehearsal`.

## Handoff

Each task gets a fresh implementer and independent review. No push/merge/deploy until Task 5 passes and a final whole-branch review confirms no production data or secrets were touched.
