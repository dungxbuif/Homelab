# RelayHub Durable Rooms Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver authenticated rooms with durable state, application handlers, membership and scheduled work across server replicas.

**Architecture:** The Centrifugo fork stores room state, deduplication records, membership and alarms in PostgreSQL. Compare-and-set and a transactional outbox coordinate replicas; configured HTTP handlers run outside database transactions. Fork SDKs expose typed APIs over standard RPC.

**Tech Stack:** Go/pgx, PostgreSQL, Centrifugo RPC/publications, TypeScript and Go SDKs, React/Playwright.

**Spec:** [Centrifugo fork design](../specs/2026-10-31-relayhub-centrifugo-fork-design.md). Prerequisite: [foundation plan](2026-10-31-relayhub-centrifugo-foundation.md), F1–F6.

## Global Constraints

- Room identifiers are 1–128 UTF-8 bytes, compared exactly without Unicode normalization.
- Room state is a JSON object limited to 64 KiB encoded UTF-8; command payloads are at most 16 KiB.
- Versions are unsigned decimal strings on the wire, including values above JavaScript's safe integer range.
- Command IDs are UUIDs; reuse with different request content is a conflict.
- Custom handlers are initially configured HTTP endpoints, with a 2-second timeout and redirects disabled. No client-supplied handler URL.
- Membership heartbeats run every 10 seconds, expire after 30 seconds, and carry a connection generation.
- Idle handler caches unload after 60 seconds without local members or work. State remains in PostgreSQL.
- Alarm leases last 30 seconds; callbacks are at least once and completion requires the current fencing generation.
- Source stays inside the existing project/nested repos. No runtime code in the vault; no production database work during these tasks.

## Review Focus

1. Two replicas write the same version, or a retry reuses an ID with another payload — R1/R2 must avoid lost updates and duplicate effects.
2. Publication succeeds but the worker crashes before marking its outbox row — R2/R4 must tolerate repeated notifications and version gaps.
3. A process disappears without leave callbacks, then its old generation returns — R3 must expire membership without removing the replacement.
4. A canceled alarm's expired worker completes after a new claim — R3 must reject stale completion; external effects remain at least once.
5. State versions exceed `2^53`, or the client disconnects during a mutation — R1/R4 must preserve exact versions and retry identity.

---

## File map and shared interfaces

Paths are relative to `/home/dungxbuif/workspace/projects/RelayHub`. Server files live inside `third_party/centrifugo/internal/relayhub/rooms/`; its SQL migrations are embedded in that package and affect only its own schema, never Rust identity or upstream broker tables.

| Files | Responsibility |
|---|---|
| `third_party/centrifugo/internal/relayhub/rooms/{types.go,store.go,store_test.go,migrations/0001_rooms.sql}` | State, command identity and atomic commit |
| Same directory: `handler.go`, `rpc.go`, `outbox.go` and matching `_test.go` files | External handler boundary, RPC and publication delivery |
| Same directory: `membership.go`, `alarms.go`, `lifecycle.go`, matching tests, `migrations/0002_lifecycle.sql` | Expiration, fenced work and cache unloading |
| `third_party/centrifuge-js/src/{rooms.ts,rooms.test.ts}`; `third_party/centrifuge-go/{rooms.go,rooms_test.go}` | Typed room facade and event reconciliation |
| `web/remake-admin/src/RealtimeStudio.tsx`, `web/remake-admin/tests/realtime.spec.ts` | Room snapshot, test command, membership and alarm visibility |
| `tests/realtime/{rooms.test.mjs,fixtures/room-handler.mjs}` | Two-replica failure tests with a controlled handler |

Go contract types in `rooms/types.go`: `Key{WorkspaceID,AppID,Room string}`, `Snapshot{Version string; State json.RawMessage}`, `Command{ID,ExpectedVersion,Handler string; Payload json.RawMessage}`, `CommitRequest{Key Key; Command Command; State,Result json.RawMessage}`, `CommitResult{Snapshot Snapshot; Result json.RawMessage; Replayed bool}`, `Event{ID string; Key Key; Version string; State json.RawMessage}`. JSON uses snake_case, except the internal nested `Key` is never accepted as client authorization. PostgreSQL versions use `numeric(20,0)` with a check from zero through `18446744073709551615`; increment overflow is an explicit conflict, not wraparound.

RPC methods: `relayhub.rooms.v1.snapshot`, `.command`, `.members`, `.alarm_set`, `.alarm_cancel`. Inputs carry `room`; the server obtains workspace/app from F3 `ScopeFromClient`. Mutations use `RpcOutcome` from F1; snapshots use the same envelope. A nonexistent authorized room reads as `{version:"0",state:{}}`; first commit creates it. `command` requires `id`, `expected_version`, `handler`, `payload`; a configured built-in `state.replace` accepts the replacement object. Handler names select configured endpoints, never user URLs.

Execution order: R1 → R2; R3 follows R1 and joins R2 for lifecycle callbacks; R4 follows R2/R3. Keep these dependent changes sequential within the server fork.

### Task R1: Commit state and command identity atomically

**Files:** Create `rooms/{types.go,store.go,store_test.go,migrations/0001_rooms.sql}` in the server fork; extend `contracts/realtime/v1/{schema.json,fixtures.json}` in the parent.

**Interfaces:** Produces `NewStore(pool *pgxpool.Pool)*Store`, `(*Store).Migrate(ctx context.Context)error`, `Snapshot(ctx context.Context,key Key)(Snapshot,error)`, `LookupCommand(ctx context.Context,key Key,command Command)(*CommitResult,error)`, `Commit(ctx context.Context,request CommitRequest)(CommitResult,error)`, sentinel errors `ErrConflict`, `ErrInvalidInput`, `ErrUnavailable`. Pool creation/ownership belongs to fork startup, using a dedicated configured DSN.

- [ ] Write `TestCommitAcrossReplicas`: concurrent commits from two pools at version `"0"` produce exactly one success and one conflict; durable outbox count is one. Retrying the winning ID/body returns the original result with `Replayed=true`; changing payload or expected version under that ID conflicts. Version `"9007199254740993"` increments exactly. Add size/JSON-object validation, overflow, rollback and restart-read tests.
- [ ] Run in server fork `GOWORK=off go test ./internal/relayhub/rooms -run 'TestCommit|TestSnapshot'`; expect FAIL for missing store. Use the disposable F1 PostgreSQL service with two independent pools.
- [ ] Implement validated commands, canonical JSON request hashing and transactionally stored command result/state/outbox. The dedup key is `(workspace_id,app_id,room,command_id)`; immutable request hash includes handler, expected version and payload. Check dedup before stale-version rejection. CAS under a transaction serializes creation and updates; no external handler calls inside transactions. Keep successful command identities for the room lifetime in this release, rather than silently expiring retry safety.
- [ ] Run the focused command with `-race`; expect PASS. Kill a transaction before commit and assert neither state nor outbox is visible; inspect schema constraints directly in integration tests.
- [ ] Commit inside the server fork `git commit -m "feat: persist room state with idempotent commands"`; commit contract fixtures separately in the parent. Do not mark the fork feature available yet.

### Task R2: Execute handlers and publish durable room events

**Files:** Create `rooms/{handler.go,handler_test.go,rpc.go,rpc_test.go,outbox.go,outbox_test.go}`; modify server `internal/relayhub/{rpc.go,service.go}`, config/startup wiring; create parent `tests/realtime/{rooms.test.mjs,fixtures/room-handler.mjs}`.

**Interfaces:** Consumes R1 store and F3 `authz.Scope`. Produces `Handler.Execute(ctx context.Context,key Key,snapshot Snapshot,command Command)(HandlerResult,error)` with `HandlerResult{State,Result json.RawMessage}`; `Executor.Command(ctx context.Context,scope authz.Scope,room string,command Command)(CommitResult,error)`; `Outbox.Run(ctx context.Context)error`. Import the shared `internal/relayhub/authz` package; `rooms` must not import its composing parent package. Handler callbacks receive `{key,snapshot,command}` and return `{state,result}`; lifecycle/alarm callback metadata is part of the command payload with stable idempotency identity.

- [ ] Write `TestHandlerCASAndOutbox`: a handler responding after another commit gets a conflict and cannot overwrite newer state; duplicate completed command does not call the handler again. HTTP redirect/timeout/invalid or oversize state fails without persistence. Simulate broker outage, then restart the worker: state survives and the event eventually publishes. Simulate publish-before-worker-crash: repeated event keeps the same ID/version. Unauthorized scope never invokes the handler.
- [ ] Run `GOWORK=off go test ./internal/relayhub/rooms -run 'TestHandler|TestOutbox'`; expect FAIL for missing executor/workers.
- [ ] Implement snapshot → dedup lookup → configured HTTP/built-in handler → CAS commit, propagating an idempotency key containing the tenant/room/command identity. Do not automatically rerun an external handler after a version conflict. Authenticate configured endpoints using secret references; bound request/response sizes and time. Add outbox lease/fence fields, retry with backoff capped at 30 seconds, and acknowledge publication only after broker acceptance; delete acknowledged payload rows after 24 hours, preserving command dedup results. Register RPC and publish ordinary versioned room events only after commit.
- [ ] Run focused tests and F1 `--suite rooms --server fork --case state-handler-outbox`; expect these selected cells PASS. Run a two-replica broker-loss case and verify bounded worker concurrency of four and clean shutdown; do not claim exactly-once publication or external effects.
- [ ] Commit server and parent test files in their respective repos: `git commit -m "feat: execute room handlers with transactional notifications"`.

### Task R3: Reconcile membership and execute fenced alarms

**Files:** Create `rooms/{membership.go,membership_test.go,alarms.go,alarms_test.go,lifecycle.go,lifecycle_test.go,migrations/0002_lifecycle.sql}`; modify server client hook composition, room RPC and lifecycle worker wiring.

**Interfaces:** Produces `Membership.Join(ctx context.Context,key Key,connection,generation,subject string)error`, `Heartbeat(ctx context.Context,connection,generation string)error`, `Leave(ctx context.Context,connection,generation,reason string)error`, `Members(ctx context.Context,key Key)([]Member,error)` with `Member{Subject,Connection,Generation string; ExpiresAt time.Time}`. `Alarms.Set(ctx context.Context,key Key,id string,due time.Time,handler string,payload json.RawMessage)(Alarm,error)`, `Cancel(ctx context.Context,key Key,id string)error`, `Run(ctx context.Context)error`; `Alarm{ID string; Generation uint64; DueAt time.Time; State string}`. `Lifecycle.Run(ctx context.Context)error` reaps membership and idle caches.

- [ ] Write `TestMembershipGeneration` and `TestAlarmFencing`: crash one of two replicas, advance the test clock 30 seconds, and assert an expiry event rather than clean leave; old heartbeat/leave cannot affect the new generation. Concurrent claims invoke one active lease; a callback past lease expiry cannot mark a successor complete. Cancellation prevents later claims, and late completion cannot undo cancellation. Restart persists pending alarms. At 60 idle seconds, cache unloads; reactivation reads the same snapshot.
- [ ] Run `GOWORK=off go test -race ./internal/relayhub/rooms -run 'TestMembership|TestAlarm|TestIdle'`; expect FAIL for missing lifecycle behavior.
- [ ] Implement database clock-based leases with injectable clocks in unit tests. Membership tracks successful subscriptions, not attempted subscriptions; hook unsubscribe/disconnect/refresh without replacing upstream callbacks. Lifecycle callbacks `activate`, `join`, `leave`, `expire`, `idle` are durable queued events with stable idempotency IDs and at-least-once delivery; `activate`/`idle` are per replica activation generation. Dispatch them through configured handlers, applying any state change with R2 CAS. Alarms use `(room,id)` identity; set replaces due/payload by incrementing generation and clearing an old claim; cancellation increments generation. Retries use bounded backoff and the stable execution ID. No automatic cancellation of already emitted external side effects.
- [ ] Run focused tests and the `rooms` suite with `--case lifecycle-alarm`, including failover/handler timeout. Expect PASS without real sleeps in unit tests; real two-replica tests establish lease behavior. Flip capability `rooms` to `1` when all server room RPCs and server tests are available; reject any unimplemented method explicitly. R4 owns the final unfiltered product room suite.
- [ ] Commit server files only: `git commit -m "feat: add reconciled room lifecycle and durable alarms"`.

### Task R4: Expose rooms in SDKs and dashboard

**Files:** Create JS `src/{rooms.ts,rooms.test.ts}`, Go `rooms.go`, `rooms_test.go`; modify their RelayHub facade exports. Create parent `web/remake-admin/src/RealtimeStudio.tsx`, `web/remake-admin/tests/realtime.spec.ts`; modify `web/remake-admin/src/{api.ts,Workspace.tsx}`, product SDK exports/manifests, and room matrix tests.

**Interfaces:** JS `RelayHubRealtime.room(id:string):Room`; `Room.snapshot():Promise<Snapshot>`, `command(command:Command):Promise<CommitResult>`, `members():Promise<Member[]>`, `setAlarm(input:{id:string,due_at:string,handler:string,payload:unknown}):Promise<Alarm>`, `cancelAlarm(id:string):Promise<void>`, `subscribe(onSnapshot:(s:Snapshot)=>void):()=>void`. Go equivalents: `(*RelayHub).Room(id string)*Room`, methods `Snapshot`, `Command`, `Members`, `SetAlarm`, `CancelAlarm`, `Subscribe`, each with `context.Context` and typed result/error; `Subscribe` returns `func()` plus error. JSON date fields use RFC3339 UTC and wire alarm generations are decimal strings, not JS numbers.

- [ ] Write SDK `room_retry_and_gap` tests: same command ID survives a reconnect; repeated event does not notify twice; a version gap reloads snapshot; versions above `2^53` remain strings. Browser test creates state through `state.replace`, observes another client's update/membership, schedules/cancels an alarm, and receives an explicit conflict after stale edit. Cross-workspace requests fail. Assert raw credentials never enter browser storage.
- [ ] Run fork tests and `cd web/remake-admin && npm test -- realtime.spec.ts`; expect FAIL for missing room APIs/UI.
- [ ] Implement SDK room methods with F4/F5 typed RPC calls; compare versions with `BigInt`/`big.Int` or canonical decimal comparison, never JS `Number`. Subscribe before reading the initial snapshot and buffer/reconcile intervening publications to avoid a read/subscribe race. Keep buffers bounded at 64 events; overflow reloads snapshot. Add a small dashboard studio for room inspection/test commands, using same-origin session acquisition and CSRF. No production handler-code editor or uploaded runtime.
- [ ] Run JS/Go SDK tests, dashboard typecheck/build/Playwright and complete F1 `--suite rooms --server fork`; expect PASS for all room cells, including legacy and auth regressions. Confirm normal upstream clients still receive ordinary publications and unsupported room features fail clearly on upstream servers.
- [ ] Commit each repo separately with `feat: expose durable rooms in SDKs and dashboard`; proceed to collaboration. Release publication/pins are handled by C4, not assumed from local nested commits.

## Handoff and verification record

Planning only; no room schema, migration, handler or alarm has been executed. Main-agent self-review maps state/outbox to R1/R2, lifecycle/ownership failure to R3 and user-visible reconciliation to R4. Follow the [collaboration/release plan](2026-10-31-relayhub-centrifugo-collaboration.md) for final interoperability, backup restore and release gates.
