# RelayHub realtime: Centrifugo and SDK forks

Date: 2026-10-31
Status: architecture draft for review; nested source checkouts prepared and pinned on 2026-10-31. No feature implementation, package publication or deployment has been performed.

## User intent and decisions

The user wants to extend RelayHub's realtime functionality, self-host the required components in Docker/Swarm, communicate directly over private service networks, fork Centrifugo, implement PartyServer-inspired features in that fork, and fork the relevant SDKs for integration into RelayHub. Unit and compatibility tests are required. Existing SDK priorities are JavaScript/Node and Go. Code belongs under `~/workspace/projects/`; the homelab vault retains documentation only.

Two questions were sent asynchronously: which PartyServer features matter most, and whether compatibility means preserving Centrifugo's protocol/SDKs or running existing PartyServer applications unchanged. Pending answers, this draft proposes Centrifugo protocol compatibility plus new RelayHub APIs. It does not treat a missing answer as approval.

This work is separate from the paused Rust v1 completion task. Uncommitted OpenAPI changes and unrelated homelab documentation must be preserved.

## Current evidence

- The original 2026-09-10 design selected Centrifugo OSS. The archived bootstrap status explicitly says integration was not implemented. See `~/workspace/projects/homelab-legacy/relayhub/SYSTEM_DESIGN.md:16` and `planning/STATUS.md:22`.
- The later Go implementation owns a Gorilla WebSocket hub. The current Rust implementation owns Axum WebSocket routes and NATS fanout. Current tracked deployment manifests do not include Centrifugo. This is a source/history finding, not a fresh runtime inventory.
- Rust realtime and durable agent traffic currently share the `relayhub.v1` frame family but have separate routes and semantics. Replacing realtime must not silently redirect durable agent traffic to Centrifugo.
- The remake Node SDK is currently backend-only. Adding browser realtime requires a browser entry point and short-lived, scoped connection/subscription credentials.
- PartyServer extends DurableObject. Its hooks, storage, alarms and hibernation rely on that runtime. `y-partyserver` adds Yjs document synchronization and a provider; it is not a Centrifugo plugin.
- Centrifugo exposes HTTP/gRPC server APIs, standard client RPC, authentication/subscription hooks, presence and history recovery. Ordinary proxy hooks do not provide a complete reliable room lifecycle, particularly after crashes.

## Approaches considered

1. Upstream Centrifugo with external room services and SDK wrappers: least upstream maintenance, but does not deliver the user's requested server/SDK forks.
2. Centrifugo fork with isolated room extensions, plus JS/Go SDK forks integrated into RelayHub: the user's chosen direction. Retains the upstream transport and requires maintaining patches and a compatibility matrix.
3. PartyServer/workerd alongside Centrifugo: retains PartyServer's runtime model but introduces another runtime and protocol. This is an alternative if unchanged PartyServer application execution becomes a requirement.

The recommendation within option 2 is to add independent modules and extension APIs, preserving upstream behavior when extensions are disabled. A fork is not a reason to rewrite existing connection or recovery code.

## Repository and runtime boundaries

The user explicitly corrected the layout: dependency repositories belong inside the existing RelayHub project directory, not as sibling projects. The following independent Git checkouts now exist:

- `~/workspace/projects/RelayHub/third_party/centrifugo`: server baseline, with a local `relayhub` branch for future extensions.
- `~/workspace/projects/RelayHub/third_party/centrifuge-js`: browser/Node SDK baseline.
- `~/workspace/projects/RelayHub/third_party/centrifuge-go`: Go SDK baseline.
- `~/workspace/projects/RelayHub/third_party/partykit`: PartyServer/PartySocket/Yjs source reference.
- `~/workspace/projects/RelayHub`: Rust identity/durable delivery, product SDK surface, dashboard and integration tests.

The parent ignores `third_party/*/`; these are nested Git repositories, not tracked submodules. It tracks `third_party/upstreams.lock.json` and `third_party/README.md` for source pins and restore/compare/upgrade procedures. Each nested checkout has full history, an `upstream` fetch remote with pushing disabled, and `refs/relayhub/upstream-base`. No dependency installation was performed. The existing default-deny Docker context excludes the nested source trees.

The manifest separately records upstream-base and checked-out commits, which initially match. When custom commits exist, push them to owned GitHub/GitLab fork remotes and record those remotes before updating the parent pin to a fork-only commit. Parent commits do not back up ignored nested changes. Hosted fork remotes have not yet been created. Keep upstream license/notice files and use distinct package/module identities for modified SDK releases.

Pinned source baselines:

| Repository | Tag | Full upstream commit |
|---|---|---|
| Centrifugo | `v6.10.2` | `cf21c5de6be83a35e02b34e44ad40bdbc5556b9f` |
| centrifuge-js | `5.8.0` | `163dcbab9d5e23f41d1142e4631bcbabc2e2f62f` |
| centrifuge-go | `v0.13.0` | `b8ee54f4562141848b44b99125d2bfd69099e874` |
| PartyKit | `partyserver@0.5.10` | `53f0c6819bd534d80152c6a1b324cd17c9ab4e6d` |

The PartyKit snapshot contains PartyServer `0.5.10`, PartySocket `1.3.0`, and y-partyserver `2.2.0`. These are source baselines, not a verified runtime-compatible set. Pin build images when implementation starts; do not infer release behavior from floating `master` documentation.

Centrifugo remains Go. RelayHub remains Rust. JS/TS and Go remain the initial public SDK languages. This is a component integration, not another rewrite of the Rust backend.

## Feature scope proposed for the fork

| Capability | Implementation responsibility | Compatibility boundary |
|---|---|---|
| Channels, publish, subscription, presence, recovery | Reuse upstream Centrifugo | Existing client commands/replies remain unchanged |
| Room API and custom logic | Fork room module; configured HTTP/gRPC application handlers or built-in handlers | New RelayHub API; no claim that PartyServer classes run unchanged |
| Room state and snapshot/version reads | Fork module backed by PostgreSQL | Durable state explicitly separate from history cache |
| Room membership and lifecycle | Fork connection/subscription integration plus reconciled membership | Define clean departure, expiry and restart behavior explicitly |
| Scheduled room work | Durable alarm records and claimed execution | At-least-once execution with idempotency, not Cloudflare scheduling compatibility |
| Collaborative documents and awareness | Reuse a Yjs-compatible engine/provider through an adapter | Verify document interoperability; ordinary pub/sub is insufficient |
| Idle room unloading and restore | Unload in-memory handlers; restore authoritative state on activation | Does not promise Durable Objects WebSocket hibernation |

The implementation plan proposes the existing JavaScript Yjs engine in a private companion container. Its first task must prove binary update interoperability, persistence/restore and resource bounds before integrating it. This avoids translating a CRDT implementation to Go. A single server binary would change this proposed design. The requested collaboration feature remains a target, not a completed capability.

Room handlers should initially be registered server-side endpoints or trusted built-ins. Uploading arbitrary user JavaScript and executing PartyServer classes is a separate runtime and isolation requirement, pending an explicit decision.

## Protocol and SDK compatibility

Preserve Centrifugo's standard JSON/Protobuf envelopes, command IDs, errors, reconnect advice, ping/pong, subscription and history semantics. Do not add incompatible mandatory fields or repurpose command identifiers.

Expose room operations through standard `rpc` methods with an explicit namespace such as `relayhub.rooms.v1.*`; use ordinary publication payloads for versioned room events. Advertise extension versions in standard application data or a separate discovery endpoint. A fork SDK connected to an upstream server must retain baseline functionality and report a clear unsupported-feature result for extension calls. Feature detection must not assume that an upstream server cannot have its own application RPC methods.

The product SDK provides a coherent RelayHub entry point and room API over the fork SDK. It owns token acquisition and product-level identities; upstream-derived SDK code continues owning reconnect, subscription bookkeeping and protocol parsing. Avoid two simultaneous reconnect loops.

Browser code receives short-lived connection and subscription tokens. Application/agent credentials and the Centrifugo server API key remain server-side. Every room is bound to authenticated workspace and application identity; a client-supplied channel or room name is never sufficient authorization.

The old RelayHub realtime frames are not wire-compatible with Centrifugo. Keep the existing realtime endpoint during migration or explicitly release a versioned SDK transition. Preserve durable agent endpoints, frames, lease fencing, ACK/retry/replay and CLI behavior throughout this work.

The existing durable endpoint is `/api/v1/socket`. Existing realtime endpoints are `POST /api/v1/realtime` and `GET /api/v1/realtime/{channel}`. Their compatibility suite must preserve binary payloads and size limits, authentication, and the HTTP `202 {status, observed_recipients}` receipt. A successful Centrifugo publish is not a delivery count; do not fabricate that receipt field from the publish result. Keep the old adapter semantics or make a separately versioned receipt change.

Current Rust realtime explicitly has no replay after reconnect. Preserve that behavior for existing endpoints; history/recovery belongs to explicitly enabled new channel/API capabilities. Do not make old consumers receive unexpected replayed messages during a transport migration.

Centrifugo JWT `channels` configures automatic subscriptions; it is not an authorization allowlist. Enforce channel permissions separately through subscription tokens or validated backend policy. RelayHub API-key revocation and Centrifugo JWT expiry/refresh are different mechanisms: define and verify how revocation reaches active connections rather than silently extending the current access lifetime.

Builder-review decisions: run the new realtime path alongside existing endpoints first; cutover is explicit and versioned, with no automatic redirect of old WebSocket traffic. Revocation must reject new operations and terminate affected active sessions through an active invalidation/revalidation path, not JWT expiry alone. Current Rust sockets revalidate approximately every 250 ms plus authentication latency; that is implementation behavior, not a hard latency SLA. Preserve the existing revocation acceptance test and add equivalent coverage for the fork, including a missed invalidation event and credential-store outage. Do not announce a stronger timing guarantee until fault tests establish it.

PartySocket/YProvider are not interchangeable with Centrifugo SDKs. Standard WebSocket transport does not imply application-protocol compatibility. An optional Party-style facade needs its own declared API subset and tests; full PartyServer source compatibility is not assumed.

## State correctness and failure behavior

Use a workspace/app/room key and a monotonic state version. The room mutation path needs a single authoritative ordering mechanism. The proposed implementation uses database transactions with per-room serialization and durable command IDs for retries; an in-memory lock alone cannot coordinate replicas.

State mutations and notification outbox rows commit together. External handler effects are not exactly-once: provide idempotency IDs, bounded execution time and explicit retry policy. Do not hold a database transaction open while making an arbitrary HTTP handler call; use an explicit state/version protocol and reject stale writes.

Alarm records survive process restart and use fenced claims, so an expired worker cannot overwrite a successor. User callbacks must tolerate duplicate execution. Define cancellation and late completion behavior in the implementation contract.

Membership uses authenticated connection generations and expirations. A process crash cannot deliver a normal close callback; reconcile expired membership and distinguish it from a clean leave. Lifecycle hooks are not an authoritative business transaction log.

For collaborative documents, persist accepted updates before acknowledging durable acceptance, preserve document/workspace identity, test full-state catch-up after history expiry, and verify concurrent/offline edit convergence against the reference implementation. Awareness/presence remains ephemeral. Snapshot compaction must preserve the same document state after restore.

## Docker and private networking

Deploy the fork as a separate portless Swarm service. The checked-in Rust stack already defines a private `relayhub-v1` overlay and joins `edge-http-net` for ingress. Final network placement must follow the live inventory at deployment time.

Rust talks to Centrifugo directly by service DNS using its authenticated HTTP or gRPC server API. Configure a separate internal listener for server API, admin and metrics. Public Traefik file-provider routes expose only the chosen client connection endpoints and RelayHub's public API/UI. Private networking does not remove authentication requirements.

Client realtime traffic can terminate directly at Centrifugo through Traefik. RelayHub remains responsible for issuing credentials and enforcing workspace/app policy. Authorized internal consumers can use private endpoints; end-user applications never receive a global server API key.

PostgreSQL remains on Pi5 with a dedicated database/user and verified Databasus enrollment if new storage is needed. Do not put authoritative room/document state into VM100 local files. Redis can provide ephemeral presence/history; its loss must not erase durable state. NATS JetStream remains responsible for the existing durable delivery transport.

Swarm secret references and 1Password mappings must be documented without values. No host port, DNS, secret, database or runtime change is made by this design.

## Required verification

Unit tests alone do not establish compatibility. Run upstream tests unchanged as well as fork tests, then run independent client/server combinations against real services:

| Client | Server | Required result |
|---|---|---|
| Upstream JS/Go SDKs | Upstream server | Establish reference behavior |
| Upstream JS/Go SDKs | Fork server | Baseline behavior preserved |
| Fork JS/Go SDKs | Upstream server | Baseline preserved; extensions fail explicitly when absent |
| Fork JS/Go SDKs | Fork server | Baseline plus declared extensions |
| RelayHub SDKs/dashboard | Integrated Rust + fork deployment | Product auth, realtime and room behavior work together |
| Existing durable SDK/CLI | Rust alongside fork | Offline delivery, stale-ACK rejection and drain unaffected |

Pin supported version combinations, including the previous supported baseline when upgrading. Exercise JavaScript in a real browser and Node, Go clients, and supported JSON/Protobuf combinations. Require schema/fixture checks independently of client implementations.

Required fault cases: reconnect/resubscribe, server restart, history expiry and snapshot fallback, expired/revoked credentials, unauthorized channel guessing, cross-workspace access, malformed frames, slow consumers and bounded queues, concurrent room mutations, duplicate RPC/alarms, room owner loss, stale writes, persistence outage, concurrent/offline document edits and restore. Cross-replica tests must prove ordering and ownership behavior; a single-node unit test cannot.

Do not compare nondeterministic connection IDs byte-for-byte. Compare observable semantics, permissions, ordering guarantees, errors and recovery outcomes. Protocol extensions must not change baseline behavior when disabled.

## Delivery and review gates

First approve the compatibility target and feature scope. Then write the implementation plan around independent server, JS SDK, Go SDK and RelayHub integration work. Keep each fork's upstream baseline tests green before adding extensions. Establish the compatibility harness early rather than after implementation.

Implement and verify room functionality before claiming PartyServer-like behavior. Prove the collaboration engine choice separately. Do not claim support for the entire PartyKit monorepo: scheduling, synchronization and collaboration packages have distinct contracts.

A release needs immutable artifacts, passing compatibility/failure tests, an exercised restore, a defined rollback and a recorded canary result. Production cutover is a separate reviewable change; building the fork does not authorize replacing production data or endpoints.

## Open product decisions

1. Is the target Centrifugo compatibility plus RelayHub room APIs, or unchanged PartyServer source/client compatibility?
2. Are room logic/state and Yjs collaboration both required for the first fork release, or should one be delivered first?
3. If collaboration needs an additional runtime, is a companion container acceptable, or is a single server binary a hard requirement?

Questions 2 and 3 affect sequencing and engine selection; they do not prevent checking the baseline protocol and existing SDK contracts.

## Planning defaults for review — 2026-10-31

These are concrete engineering proposals for the requested implementation plan, not answers attributed to the user. Review the [foundation plan](../plans/2026-10-31-relayhub-centrifugo-foundation.md), [room plan](../plans/2026-10-31-relayhub-centrifugo-rooms.md), and [collaboration/release plan](../plans/2026-10-31-relayhub-centrifugo-collaboration.md) together. Execute with subagents as previously requested, after plan review; do not resume the separately paused Rust completion task implicitly.

- Deliver Centrifugo compatibility first, room state/handlers/alarms second, Yjs collaboration third. Both feature groups are in the proposed release; unchanged PartyServer applications and PartySocket wire compatibility are outside it.
- Code stays in `~/workspace/projects/RelayHub`, with fork source in its existing ignored `third_party` subdirectories. Operational automation belongs in `~/workspace/projects/homelab-ops`; this vault holds plans/runbooks/evidence.
- Baseline toolchains: Go 1.27.1, Rust 1.99, Node 22 or newer. Resolve and record immutable build image digests at implementation time. Preserve upstream licenses and existing JSON/Protobuf transports.
- New API: `POST /api/v1/apps/{app_id}/realtime/session`; discovery RPC: `relayhub.capabilities.v1`; room RPC namespace: `relayhub.rooms.v1`; document RPC namespace: `relayhub.docs.v1`. Keep old realtime and durable endpoints unchanged.
- Connection and subscription JWTs expire after 60 seconds. Session grants are ephemeral Redis entries with the same TTL; they contain the source credential digest, never plaintext. Rust alone revalidates that digest against identity storage. Internal grant checks run every 250 ms, batch at most 128 distinct grants, and time out after 2 seconds. Failed validation denies new operations and disconnects affected sessions; healthy-path revocation must pass the existing 3-second acceptance window. This is a test target, not an outage SLA.
- Room identifiers are 1–128 UTF-8 bytes, compared exactly without Unicode normalization. Channel names are computed server-side from workspace UUID, app UUID and base64url room bytes. Subscription credentials are bound to the exact channel and connection; automatic JWT subscriptions do not grant permission.
- Room state is a JSON object limited to 64 KiB encoded UTF-8; command payloads are at most 16 KiB. Versions are unsigned decimal strings on the wire, including values above JavaScript's safe integer range. Command IDs are UUIDs; reuse with different request content is a conflict.
- Room mutations use PostgreSQL compare-and-set with durable deduplication and a transactional outbox. State changes increment the version once. Outbox publication is at least once; SDKs deduplicate by event ID/version and reload snapshots on gaps. State conflict is explicit, not an automatic rerun of an external handler.
- Custom handlers are initially configured HTTP endpoints, with a 2-second timeout and redirects disabled. No client-supplied handler URL. Handler calls carry an idempotency key and execute outside database transactions. Lifecycle hooks describe activation/clean leave/expiry; they do not promise a globally unique Durable Object actor.
- Membership heartbeats run every 10 seconds, expire after 30 seconds, and carry a connection generation. Idle handler caches unload after 60 seconds without local members or work. State remains in PostgreSQL. Alarm leases last 30 seconds; callbacks are at least once and completion requires the current fencing generation. Cancellation prevents future claims but cannot undo an already running external effect.
- Yjs companion dependencies start at `yjs@13.6.30`, `y-protocols@1.0.7`, and `lib0@0.2.117`, resolved in the pinned PartyKit lockfile. It performs stateless merge/diff operations; Go owns authorization, durable state and publication. No new durable service files on VM100.
- Document updates are at most 256 KiB; full snapshots at most 1 MiB; companion HTTP bodies at most 2 MiB and requests time out after 2 seconds. Awareness entries are at most 8 KiB, expire after 30 seconds and are never durable. Reject oversize or malformed input before durable acceptance. Go exposes binary document operations, not a Yjs editing engine.
- New service listeners use client port 8000 and private API/admin/metrics port 9000, with no published host ports. Public route prefix is `/realtime`, stripped before forwarding `/connection/websocket`; deny public access to internal APIs. The Yjs companion is private on port 8090. Production secrets use Swarm secrets with 1Password item/field mappings, never values in Git.
- Release gate: every declared client/server combination passes, disposable backup restore proves room/document state, immutable images and packages are recoverable from both owned Git remotes, and a reviewed canary/rollback runbook exists. Production activation remains a separate operator-authorized step.

## Review evidence

An independent SDK audit identified the durable/realtime split, old no-replay behavior, HTTP receipt compatibility and the distinction between JWT automatic subscriptions and authorization. A separate builder review asked about active revocation and migration; the decisions above resolve those for the proposed baseline. No product tests were run: this change contains a design document only.

## Primary references

- [Centrifugo server API](https://centrifugal.dev/docs/server/server_api)
- [Centrifugo client protocol](https://centrifugal.dev/docs/transports/client_protocol)
- [Centrifugo backend proxies](https://centrifugal.dev/docs/server/proxy)
- [Centrifugo internal listeners](https://centrifugal.dev/docs/server/configuration#custom-internal-port)
- [Centrifugo SDK matrix](https://centrifugal.dev/docs/transports/client_sdk)
- [PartyServer](https://github.com/cloudflare/partykit/blob/main/packages/partyserver/README.md)
- [Y-PartyServer](https://github.com/cloudflare/partykit/blob/main/packages/y-partyserver/README.md)
- [Yjs WebSocket provider](https://docs.yjs.dev/ecosystem/connection-provider/y-websocket)
- [Centrifugo release candidate](https://github.com/centrifugal/centrifugo/releases/tag/v6.10.2)
- [JS SDK release candidate](https://github.com/centrifugal/centrifuge-js/releases/tag/5.8.0)
- [Go SDK release candidate](https://github.com/centrifugal/centrifuge-go/releases/tag/v0.13.0)
