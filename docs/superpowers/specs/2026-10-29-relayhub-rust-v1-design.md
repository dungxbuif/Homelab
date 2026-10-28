# RelayHub Rust v1 — design baseline

Status: scope agreed in conversation; detailed defaults below are proposals for review.
Implementation repository: `/home/dungxbuif/workspace/projects/RelayHub`.
Documentation remains in the homelab vault. No implementation or production change is authorized by this document.

## Product and agreed scope

A self-hosted service for connecting applications through realtime sockets, durable messages and HTTP webhook tunnels. Rust replaces the Go backend; new public contracts are allowed. Retain PostgreSQL, NATS JetStream and Redis. Provide a Rust CLI like ngrok and Node.js/TypeScript and Go SDKs.

Only administrators create accounts. Each user receives a separate workspace. Every application, credential, endpoint, agent, event, delivery and channel belongs to a workspace. A connection never supplies a trusted workspace identity: derive it from authenticated credentials and check every operation. System administration and application credentials are distinct.

Agents connect outbound using WebSocket. Offline agents receive queued work when they reconnect. Dashboard supports configuration, online status, pending/failed delivery inspection, replay, realtime tests and durable event tests. Webhook endpoints select synchronous or asynchronous handling and offline behavior.

Full TCP tunneling, website proxying, remote functions, billing, public signup and compatibility with old SDKs are outside this proposed v1. Workspace invitations/roles beyond system-admin and workspace-owner are deferred; separate workspaces are the confirmed requirement.

## Approaches

Considered Rust/PostgreSQL only, Rust/PostgreSQL/JetStream, and retaining the existing PostgreSQL/JetStream/Redis architecture. User selected the existing architecture. This preserves broker and distributed connection support, at the cost of multiple stores and recovery coordination. This does not require copying all old features.

## Store ownership and delivery

PostgreSQL owns identity, configuration, event acceptance, delivery state, audit and a transactional outbox. JetStream owns durable transport, not the sole authoritative acceptance receipt. Redis owns expiring presence, gateway ownership, rate counters and synchronous response rendezvous. Redis loss must not lose accepted durable messages.

Accept event and outbox in one transaction. Publish with a stable delivery identifier and wait for broker acknowledgement before marking outbox sent. Duplicate publications remain safe beyond the broker deduplication window: PostgreSQL delivery state gates claims. Agent success is persisted before broker ACK. Delivery is at least once; application side effects require consumer idempotency using event_id. Never promise exactly once.

Each attempt has a fenced lease token. ACK from an expired attempt is rejected. For sync HTTP, one response wins via a compare-and-set; late/duplicate responses are recorded but cannot answer a different waiting request. Replay creates a new delivery generation, retaining event identity and the original audit trail.

## Proposed precise defaults

These values are engineering proposals, not user-selected requirements:

- API prefix `/api/v1`; socket subprotocol `relayhub.v1`; new contracts are namespaced independently of old deployment.
- Payload maximum 1 MiB, including HTTP request/response body; no HTTP streaming or WebSocket upgrade tunneling in v1.
- Sync timeout default 15 seconds, configurable 1–30 seconds.
- Async replies 202 only after acceptance commit. Sync offline policy is `queue` (202) or `reject` (503, no enqueue).
- Sync timeout policy is `continue` (202 with event ID) or `expire_pending` (504; cancel only work not yet claimed). Claimed work remains outcome-unknown and may complete; timeout is not proof of cancellation.
- Durable retention 7 days; workspace limits 10,000 outstanding deliveries and 100 MiB outstanding payload bytes. Admission beyond either returns 429 before commit. Enforce limits transactionally; no unbounded fallback.
- Lease 60 seconds; heartbeat 20 seconds; maximum attempt runtime 300 seconds. Up to 5 processing attempts with delays 1, 5, 30, 120 seconds. Offline waiting does not consume attempts. Exhausted work enters DLQ; retention expiry is separately visible.
- Presence heartbeat 20 seconds, expiry 60 seconds; maximum 16 in-flight deliveries per agent.
- Realtime is ephemeral. Publish with no subscribers succeeds with zero recipients; dashboard displays that fact. Durable tests always use normal persistence and delivery semantics.
- Admin provisioning uses a single-use password setup token expiring after 24 hours. Store hashes, never plaintext token values. Sessions are revocable; browser cookies require TLS and CSRF protection.

## Security and endpoint behavior

Endpoint authentication is configured independently of app credentials. Support a shared bearer secret or explicitly enabled public webhook endpoint; redact credentials from logs. Provider-specific signature adapters are deferred. App/agent keys are scoped, revocable and stored as hashes. Bind SDK browser realtime tokens to workspace/channel permissions with short expiry.

CLI configuration maps endpoint IDs to fixed local HTTP URLs. Remote frames cannot choose arbitrary destinations. Disable redirects, block metadata endpoints, strip hop-by-hop headers and internal authentication, preserve duplicate safe headers and encode binary bodies as base64. Users may explicitly configure localhost/LAN targets; do not make this a general open proxy. Public caller identity must not become local service credentials implicitly.

## Acceptance and migration

Test real PostgreSQL, JetStream and Redis plus two gateway replicas. Demonstrate offline enqueue, restart recovery, stale ACK rejection, queue limits, workspace isolation, sync late response and both SDKs/CLI against one protocol fixture set. Test realtime separately from durable delivery.

Build alongside existing Go deployment, using separate DB/schema, broker subjects, Redis namespace and staging route. No automatic migration of pending old work. At cutover, stop old producers, drain or explicitly reconcile old outstanding deliveries, then move one integration at a time. Retain old deployment for rollback; no deletion or production replacement as part of planning.

Release requires backup/restore evidence, verified secrets references, telemetry without payload/secret leakage, pinned artifacts and a separately approved cutover. PostgreSQL on the shared Pi5 cluster must use a dedicated DB/user and verified Databasus enrollment.
