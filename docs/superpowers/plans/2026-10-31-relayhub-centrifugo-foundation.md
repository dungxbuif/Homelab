---
type: Plan
title: RelayHub Centrifugo Foundation Implementation Plan
generated:
  by: "process:vault-import"
  at: "2026-10-31T16:00:00+07:00"
stale_after: "2026-12-30T16:00:00+07:00"
---

# RelayHub Centrifugo Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an authenticated Centrifugo path and fork SDKs alongside RelayHub's existing realtime and durable APIs.

**Architecture:** Rust owns identity and short-lived grants; the Go fork owns connection policy and transport. Standard RPC exposes capability discovery; product SDKs reuse upstream reconnect machinery. This is the entry plan, followed by [rooms](2026-10-31-relayhub-centrifugo-rooms.md) and [collaboration/release](2026-10-31-relayhub-centrifugo-collaboration.md).

**Tech Stack:** Rust/Axum/sqlx, Go/Centrifugo, Redis, PostgreSQL, TypeScript, Playwright, disposable Docker Compose.

**Spec:** [Centrifugo fork design](../specs/2026-10-31-relayhub-centrifugo-fork-design.md), including its planning defaults awaiting review.

## Global Constraints

- Baseline toolchains: Go 1.27.1, Rust 1.99, Node 22 or newer.
- Code stays in `~/workspace/projects/RelayHub`, with fork source in its existing ignored `third_party` subdirectories. Operational automation belongs in `~/workspace/projects/homelab-ops`; this vault holds plans/runbooks/evidence.
- Connection and subscription JWTs expire after 60 seconds.
- Internal grant checks run every 250 ms, batch at most 128 distinct grants, and time out after 2 seconds.
- Keep old realtime and durable endpoints unchanged. No replay for old realtime; retain binary payloads, 1 MiB limit and `202 {status, observed_recipients}` receipts.
- Pinned baselines are Centrifugo v6.10.2, JS 5.8.0, Go v0.13.0 and PartyKit partyserver@0.5.10; use the full commits in `third_party/upstreams.lock.json`, not moving tags.
- Do not absorb the paused Rust task's dirty `identity.rs`, `tests/identity.rs` or `scripts/remake-acceptance.sh`. Implement in isolated worktrees and reconcile only owned hunks. No production changes in this plan.

## Review Focus

1. Guessed cross-tenant channels and Unicode/empty/oversize names must not bypass policy — Tasks F2/F3.
2. A revoked credential, missed invalidation or unavailable credential store must stop access — F2/F3.
3. Missing extensions or an unrelated upstream application RPC must not break baseline SDK operation — F4/F5.
4. Browser bundles must contain no application keys, Node-only imports or duplicate reconnect loop — F6.
5. Malformed frames, slow consumers and restarts must preserve upstream behavior and old API guarantees — F1/F6.

---

## Working layout and contracts

All source paths below are relative to `/home/dungxbuif/workspace/projects/RelayHub`. Each nested Git repo needs its own isolated branch/worktree, placed beneath this project, when implementation starts. `GOWORK=off` is mandatory for nested Go modules and `sdks/remake/go`. PartyKit is read-only reference. Do not copy all its packages into the fork.

| Files | Responsibility |
|---|---|
| `contracts/realtime/v1/schema.json`, `fixtures.json` | New session, capabilities and extension result schemas; independent of frozen `contracts/v1` |
| `tests/realtime/compose.yaml`, `package.json`, `harness.mjs`, `matrix.test.mjs`, `browser.spec.ts`, `go/probe_test.go`, `go/go.mod`, `playwright.config.ts`; `scripts/realtime-compat.sh` | Isolated servers, pinned client probes, fault injection and matrix report |
| `rust/src/realtime_session.rs`, `rust/tests/realtime_session.rs` | Grant issuance/revalidation and authenticated internal policy endpoint |
| `third_party/centrifugo/internal/relayhub/{policy.go,rpc.go,service.go}`, `internal/configtypes/relayhub.go` | Optional transport extension, policy polling and discovery |
| `third_party/centrifuge-js/src/relayhub.ts`, `third_party/centrifuge-go/relayhub.go` | Additive SDK discovery and typed RPC result handling |
| `sdks/remake/browser/`, `sdks/remake/node/src/realtime.ts`, `sdks/remake/go/realtime.go` | Product token providers and client factories |

Wire types: `Access = "read" | "write"`; `RoomGrant = {room:string, access:Access}`. `SessionRequest = {rooms:RoomGrant[],connection_id?:string}`; app UUID comes from the path and workspace from the authenticated app record. `SessionResponse = {url:string, token:string, expires_at:number, subscriptions:{room:string,channel:string,token?:string}[]}`; time is Unix seconds. Omit subscription tokens until `connection_id` is available; never issue an unbound token as a shortcut. A request contains 1–64 unique rooms; duplicate room entries are invalid. Write includes read. System admin/workspace owner may issue permitted app grants; application credentials are confined to their app; agent credentials may request read only, consistent with existing `Action::Publish` denial.

`Capabilities = {version:1, features:{rooms:0|1, documents:0|1}}`. `RpcOutcome<T> = {ok:true,value:T} | {ok:false,error:{code:"invalid_argument"|"forbidden"|"conflict"|"unavailable"|"unsupported_feature",message:string}}`. Extension application errors use this ordinary RPC data envelope; do not modify upstream protocol error numbers. Baseline discovery returns both features as zero until their tasks ship.

Execution order: F1 → F2 → F3; F4 and F5 can run in parallel after F1's schema is committed; F6 joins them. A subagent owns one repo/task at a time; the main agent handles integration and review. Use the previously requested Luna subagents where available.

### Task F1: Establish an independent baseline compatibility harness

**Files:** Create the `tests/realtime/*`, `scripts/realtime-compat.sh` and `contracts/realtime/v1/*` files listed above; create `tests/realtime/fixtures/legacy-realtime.json` and `tests/realtime/.gitignore` for generated reports.

**Interfaces:** Consumes `third_party/upstreams.lock.json`. Produces `scripts/realtime-compat.sh --suite baseline|auth|sdk|legacy|rooms|documents|all --server upstream|fork|both --report PATH [--client js|go|product|all] [--case NAME]`; returns nonzero for failure or missing selected matrix cells. Default client is `all`; `--suite all` forbids filters and requires every cell. Early tasks may select named cases; final phase gates may not omit unfinished cases. `harness.mjs` exports `startHarness({server,replicas}):Promise<{http,ws,privateApi,stop,killReplica,restartRedis}>`; service URLs are loopback addresses of an isolated Compose project.

- [ ] Write `baseline_matches_reference`: `assert.deepEqual(report.missingCells, [])`; `assert.equal(report.failed, 0)`. Matrix cells explicitly enumerate browser JS JSON/Protobuf, Node JS JSON/Protobuf, Go JSON/Protobuf against upstream/fork servers and SDKs. Add malformed frame, reconnect/history expiry and bounded slow-consumer cases; assert disconnect/recovery semantics instead of random IDs. Include old realtime binary/1 MiB/receipt/no-replay and existing durable delivery tests as the `legacy` suite.
- [ ] Run `scripts/realtime-compat.sh --suite baseline --server both --report /tmp/relayhub-baseline.json`; expect FAIL because the harness/fixtures do not exist. After scaffolding, deliberately corrupt one expected publication and verify a nonzero result before restoring it.
- [ ] Implement the CLI and harness. Build untouched upstream sources from the lock's upstream commits in separate disposable checkouts; build fork sources from their own branches. Use unique project names and allocated loopback ports, never production credentials. A cleanup trap removes only that project's resources. Reuse pinned SDK builds and keep a manifest of every matrix cell, including unsupported extension expectations. Capture raw semantic results separately from assertions; do not produce reports by counting intended tests.
- [ ] Run the baseline command and `--suite legacy --server fork`; expect all enumerated cells PASS and no skipped required cells. Store commands, exact source/image hashes and results in the generated report. Upstream harness scripts that assume fixed ports must run in isolated containers.
- [ ] Commit only F1 files in the parent repo: `git commit -m "test: establish realtime compatibility baseline"`. This harness is independently usable before any new API exists.

### Task F2: Issue scoped tokens and revalidate their source identity

**Files:** Create `rust/src/realtime_session.rs`, `rust/tests/realtime_session.rs`; modify `rust/src/{lib.rs,host.rs,identity.rs}`, `rust/Cargo.toml`, `rust/Cargo.lock`; extend session fixtures/schema from F1.

**Interfaces:** Consumes `Identity::authenticate`, `authorize`, `Action::Connect/Publish`. Produces `RealtimeSession::new(identity:Identity, redis:redis::Client, config:RealtimeSessionConfig)->Self`, `router(&self)->Router`, `issue(&self, headers:&HeaderMap, app_id:Uuid, request:SessionRequest)->Result<SessionResponse,AuthError>`, `check_grants(&self, ids:&[Uuid])->Result<Vec<Uuid>,AuthError>`. Config fields: `public_ws_url:String`, `jwt_secret:Vec<u8>`, `policy_secret:Vec<u8>`, `namespace:String`. Add crate-private `Identity::authenticate_digest(&self, hash:&[u8])->Result<Principal,AuthError>` and make `request_auth` crate-private; only the authenticated internal module may use the digest method.

- [ ] Write `session_scope_and_revocation`: assert `exp - iat == 60`, exact connection-bound subscription channel, cross-app `403`, agent write `403`, missing CSRF on cookie requests `403`, duplicate room `422`, empty/129-byte room `422`, 128-byte Unicode room accepted. Assert source key/cookie absent from the response; after credential revocation `check_grants` returns no allowed ID; Redis or PostgreSQL outage produces an error, never cached authorization. A bad internal secret is `401`.
- [ ] Run `cargo test --manifest-path rust/Cargo.toml --test realtime_session`; expect FAIL for missing module/endpoint.
- [ ] Implement the two POST routes: public `/api/v1/apps/{app_id}/realtime/session` and authenticated internal `/internal/realtime/v1/authorize` with `{grant_ids:string[]}` → `{allowed:string[]}` (maximum 128). Reuse existing identity SQL behind the private digest method. Store only digest and authoritative app/room scope in Redis with 60-second TTL and random grant ID; include that ID in signed token metadata. Use a maintained JWT library with a locked version and algorithm allowlist, not handwritten JWT cryptography. Validate the app exists in the principal's workspace. Subscription-token refresh uses the new connection ID after reconnect; accept that ID as an optional session request field validated as a Centrifugo connection identifier.
- [ ] Wire optional config into `Host::router` without adding mandatory fields to existing `Host::new` callers. Disabled integration exposes no new routes. Run the test plus `cargo test --manifest-path rust/Cargo.toml --test identity --test realtime`; expect PASS, including the existing revocation test. Add grant TTL/namespace-isolation tests and verify no credential values in logs.
- [ ] Commit only F2 changes, preserving the pre-existing OpenAPI hunks: `git commit -m "feat: issue scoped realtime session grants"`.

### Task F3: Enforce policy inside the server fork without replacing upstream handlers

**Files:** Create `third_party/centrifugo/internal/relayhub/{policy.go,policy_test.go,rpc.go,rpc_test.go,service.go,service_test.go}`, `internal/configtypes/relayhub.go`; modify its `internal/config/{config.go,validate.go}`, `internal/client/{handler.go,client.go}`, `internal/app/run.go`.

**Interfaces:** Consumes F2 policy endpoint. Produces `authz.Scope{WorkspaceID,AppID,Subject,GrantID string; Rooms map[string]string}` in a new `internal/relayhub/authz/scope.go` with `scope_test.go`, `Policy.Check(ctx context.Context, grantIDs []string)(map[string]bool,error)`, `Scope.Authorize(room,access string) error`, `Scope.Channel(room string) string`, `RegisterRPC(h *client.Handler, methods map[string]client.RPCExtensionFunc)`, `Service.Run(ctx context.Context)`. Existing extension signature is `func(client.Client, centrifuge.RPCEvent)(centrifuge.RPCReply,error)`. Verified scope is retrieved by `authz.ScopeFromClient(c StorageClient)(Scope,error)` from connection storage, where `authz.StorageClient` is the local structural interface `interface { AcquireStorage() (map[string]any, func(map[string]any)) }`. The authz package imports neither client handlers nor its composing parent, preventing cycles. Never decode client-provided scope as trusted.

- [ ] Write `TestPolicyFailClosedAndIsolation`: assert another workspace/channel and forged scope are denied; unknown/expired grant denied; revocation disconnects within 3 seconds in healthy conditions; polling still detects revocation with event delivery disabled. Timeout/store outage denies operations and closes clients. Assert 129 grants split into batches `128,1`; per-connection refresh replaces the old grant and subscription binding. `TestExtensionsDisabled` asserts the existing upstream handlers and RPC proxy still run.
- [ ] Run in `third_party/centrifugo`: `GOWORK=off go test ./internal/relayhub ./internal/client -run 'TestPolicy|TestExtensions'`; expect FAIL for missing extension/policy.
- [ ] Implement opt-in `relayhub` config and startup validation; require private policy URL/auth and JWT verification configuration when enabled. Register `relayhub.capabilities.v1` using `SetRPCExtension` after `Handler.Setup`, before listeners accept connections. Compose connection/subscription/refresh callbacks inside the existing handler; do not replace `node.OnConnect`. Enforce room scope on every operation and exact subscription tokens; client publish is disabled for room state channels. Poll distinct grants with bounded batches, expire authorization and disconnect on failure. The private client interface may gain a narrowly scoped disconnect method.
- [ ] Run the focused command, the upstream unit selection from `misc/scripts/test_packages.sh`, and F1 `--suite auth --server fork`; expect PASS. Test stop/start and graceful worker shutdown under `-race`; reject runtime reload of immutable RelayHub config with an explicit restart-required error instead of pretending it applied.
- [ ] Commit in the Centrifugo repo only: `git commit -m "feat: add scoped RelayHub realtime extension"`. Keep the parent lock at recoverable remote commits until the release task publishes this fork commit.

### Task F4: Add a browser-safe JS fork facade

**Files:** Create `third_party/centrifuge-js/src/relayhub.ts`, `src/relayhub.test.ts`; modify its `src/index.ts`, `src/browser.ts`, `src/browser.protobuf.ts`, `package.json`, lockfile and build entry configuration as required by those exports.

**Interfaces:** Consumes existing `Centrifuge.rpc(method,data)` and F1 types. Produces `RelayHubRealtime(client:Centrifuge)`, `capabilities():Promise<Capabilities>`, `call<T>(method:string,data:unknown):Promise<T>`, `UnsupportedFeatureError`. The facade owns no transport or reconnect timers. Modified package identity: `@relayhub/centrifuge`, initially private/unpublished.

- [ ] Write `discovery_is_additive`: assert baseline publish works against upstream, valid capability shape is accepted, unrelated `{version:"other"}` discovery is rejected as unsupported, a temporary transport error is preserved rather than cached as unsupported, and unknown feature calls return `UnsupportedFeatureError`. Verify both JSON and Protobuf entry exports and no Node globals in the browser bundle.
- [ ] Run in the JS fork: `yarn test --runInBand relayhub`; expect FAIL for missing facade.
- [ ] Implement discovery with strict version/shape validation, cache only successful discovery for the current connection and invalidate on reconnect. Map `RpcOutcome` application errors while retaining standard SDK transport errors. Keep upstream public exports and build variants; keep the existing upstream license notices.
- [ ] Run the focused tests, upstream tests in the isolated harness and F1 `--suite sdk --server both --client js`; expect JS matrix cells PASS and extensions absent on upstream reported explicitly. Go/product cells remain required at the final F6 gate, not silently removed from the manifest.
- [ ] Commit only in JS fork: `git commit -m "feat: add RelayHub discovery facade"`.

### Task F5: Add the equivalent Go fork facade

**Files:** Create `third_party/centrifuge-go/relayhub.go`, `relayhub_test.go`; modify its `go.mod`, `go.sum`, `errors_test.go` and canonical self-imports in `examples/`.

**Interfaces:** Consumes `(*Client).RPC(ctx,method,[]byte)`. Produces `NewRelayHub(client *Client)*RelayHub`, `(*RelayHub).Capabilities(ctx context.Context)(Capabilities,error)`, `(*RelayHub).Call(ctx context.Context,method string,input any,output any)error`, `ErrUnsupportedFeature`. `Capabilities{Version int; Features struct{Rooms,Documents int}}` uses the JSON names in F1. Modified module identity: `github.com/dungxbuif/centrifuge-go`; Go package identifier stays `centrifuge`.

- [ ] Write `TestDiscoveryCompatibility`: mirror F4 assertions, and assert canceled contexts return `context.Canceled` without leaking a reconnect worker. Check JSON/Protobuf constructors and example imports compile under the new module name.
- [ ] Run in Go fork: `GOWORK=off go test -race ./... -run TestDiscovery`; expect FAIL for missing facade.
- [ ] Implement the facade with upstream client lifecycle ownership, strict discovery validation and connection-scoped caching. Update self-imports and local example replacements; do not change protocol definitions or baseline constructor signatures.
- [ ] Run `GOWORK=off go test -race ./...` in the isolated upstream test environment and the Go SDK matrix cells; expect PASS for upstream/fork servers. Run example compilation to catch module identity conflicts.
- [ ] Commit only in Go fork: `git commit -m "feat: add RelayHub Go discovery facade"`.

### Task F6: Integrate product clients and preserve the old product contracts

**Files:** Create `sdks/remake/browser/{package.json,tsconfig.json,src/index.ts,test/realtime.test.ts}`, `sdks/remake/node/{src/realtime.ts,test/realtime.test.ts}`, `sdks/remake/go/{realtime.go,realtime_test.go}`; modify their package/module manifests and lockfiles. Extend `tests/realtime/browser.spec.ts` and `matrix.test.mjs`.

**Interfaces:** Consumes F2 `SessionResponse`, F4/F5 facades. Produces browser/Node `createRealtime({getSession:(connectionId?:string)=>Promise<SessionResponse>}):Promise<RelayHubRealtime>`; Go `NewRealtime(ctx context.Context,getSession func(context.Context,string)(SessionResponse,error))(*centrifuge.RelayHub,error)`. Product factories expose their underlying client for standard subscriptions; token providers renew via `getSession`, using the actual connection ID for subscription tokens. Browser package: `@relayhub/browser-experimental`.

- [ ] Write `browser_and_product_reconnect`: assert a real browser obtains same-origin cookie/CSRF-backed tokens and never sees the source API key; reconnect renews the connection-bound subscription token; only one transport connection exists after repeated reconnects. Existing Node agent offline delivery, stale ACK, drain and raw realtime tests remain PASS. Test legacy reconnect receives no historical publication.
- [ ] Run F1 `--suite sdk --server both` plus `--suite legacy --server fork`; expect new product/browser cases FAIL until factories exist.
- [ ] Implement factories using fork SDK token callbacks and exported client lifecycle, with a browser-specific package free of Node `crypto`, `Buffer` and `ws`. Node/Go callers provide server-side token acquisition explicitly; browser code never accepts an application secret as convenience configuration. Preserve existing agent factories and frozen fixtures.
- [ ] Run both commands again, each product SDK's existing test/typecheck/build commands, and `cargo test --manifest-path rust/Cargo.toml --test contracts --test delivery --test recovery`; expect PASS and zero missing foundation matrix cells. Collect exact dependency pins locally, not floating registry tags.
- [ ] Commit parent SDK/integration files only: `git commit -m "feat: integrate fork realtime clients alongside legacy APIs"`. Proceed to the room plan after task review; no production cutover.

## Handoff and verification record

This is a proposed plan, not executed test evidence. Main-agent self-review maps transport/auth/legacy requirements to F1–F6; room and collaboration requirements belong to the linked plans. Review the three plans as one release scope. Preserve the user's subagent execution choice after approval. Final delivery must push owned fork histories before updating parent pins, as specified in Task C4 of the collaboration plan.

Additional user-requested workstreams: [full webhooks](2026-10-31-relayhub-full-webhooks.md) and [product Docusaurus/Developer Kit](2026-10-31-relayhub-product-docs.md). Across all five plans there are 25 implementation tasks. First land F1/F2 contracts/auth, then server/SDK fork work and webhook work can proceed in separate repositories or isolated worktrees; serialize shared Rust/dashboard integration through the main agent. Product narrative can run in parallel, with feature labels tied to verified release evidence. Final release verification joins all selected workstreams; finishing one phase does not imply that the others are deployed.
