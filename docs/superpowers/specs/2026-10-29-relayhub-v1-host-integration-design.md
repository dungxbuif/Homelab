# RelayHub v1 Host Integration and Drain — Design

Status: approved by the user for v1 breaking integration because the remake has no users or compatibility obligations.

## Intent

Make the Rust remake executable as one self-hosted v1 service and close the known shutdown gap before release. The host must compose the already-tested library modules, expose the dashboard contracts, dispatch agent `Response` frames into `Responses::complete_response`, and stop new delivery claims during graceful shutdown.

## Goals

- Add one Rust host command, `relayhub serve`, with environment-based configuration for PostgreSQL, NATS, Redis, namespace and HTTP address.
- Compose identity, durable events/outbox, WebSocket gateway, webhook ingress/status, realtime and dashboard adapters without duplicating their storage rules.
- Add a server-to-agent `drain` frame. On drain, agents stop local admission/reconnect, finish already-admitted handlers up to the 30-second deadline, settle them, and close. The Gateway stops new claims while allowing ACK/Response/heartbeat for outstanding leases.
- Keep at-least-once delivery and fenced ACK/Response semantics. A timed-out or stale response remains rejected.
- Issue short-lived browser realtime tokens bound to workspace, channel and publish-only permission; never send app keys to the browser.
- Make the release rehearsal exercise the real host binary and dashboard adapters rather than only library mocks.

## Non-goals

- No full TCP tunnel, arbitrary proxy, remote functions, public signup, billing or old SDK compatibility.
- No migration of old pending work into the new namespace.
- No exactly-once business side effects; consumers still deduplicate by event ID.

## Approaches

1. Keep the library-only design and document host gaps. Smallest diff, but it cannot satisfy the v1 release goal.
2. Add a thin Rust host that composes existing routers and adds only missing adapters, then add the drain frame across the new SDKs. Recommended: it reuses tested modules and keeps the breaking surface explicit.
3. Build a separate production service layer with new persistence abstractions. Rejected as duplicate code and a larger failure surface.

The user selected approach 2.

## Frozen v1 decisions

- New `Frame::Drain { version, request_id, deadline_ms }` is server-to-agent only. `deadline_ms` is 1–30,000 and the host sends 30,000 for graceful shutdown. It needs no ACK; the socket close is the completion signal.
- A Gateway receiving shutdown broadcasts Drain to authenticated agent sockets, disables new `pending()` claims, and continues current ACK/Response/heartbeat until all outstanding leases settle or the deadline expires.
- Node and Go handlers treat Drain as a local admission cutoff. They do not reconnect after Drain, and close after current admitted work settles or 30 seconds elapse. A handler that ignores cancellation remains bounded by the socket close, not forcibly killed.
- `relayhub serve` owns migrations and starts the outbox/expiry workers. Shutdown broadcasts drain before stopping HTTP acceptance and waits at most 30 seconds.
- Dashboard APIs are same-origin cookie/CSRF routes. Workspace scope is derived from the authenticated principal. Replays require owner/admin authorization and return an audit record before the UI reports success.
- Scoped realtime tokens are opaque Redis-backed values with a 60-second TTL and workspace/channel/publish-only claims. They are accepted only by the realtime publish/subscribe adapter, never by durable event or agent routes.

## Verification shape

- Protocol fixtures and Rust/Node/Go contract tests pin the Drain shape and reject unknown fields.
- Gateway tests prove no new claim after drain, current ACK/Response still settles, stale ACK remains fenced, and deadline closes the session.
- SDK tests prove Drain stops reconnect/admission and preserves active settlement.
- Host acceptance runs `relayhub serve` against disposable PostgreSQL/NATS/Redis, exercises publish → outbox → agent response, dashboard authorization/replay/audit, scoped realtime, and graceful drain.

The existing release blockers are therefore converted into implementation gates rather than documented handoffs.
