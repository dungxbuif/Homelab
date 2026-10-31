---
type: Service
title: RelayHub internals — internal operator reference
generated:
  by: "process:vault-import"
  at: "2026-10-31T16:00:00+07:00"
stale_after: "2027-01-29T16:00:00+07:00"
---

# RelayHub internals — internal operator reference

This document is intentionally outside the public Docusaurus input tree. Public product documentation describes RelayHub's behavior and integration contracts without naming the service components behind it.

## Ownership boundary

Application developers maintain their applications, credentials and business data. The RelayHub operator maintains the runtime, durable storage, message transport, private networks, backups, secrets and recovery drills. Users do not need to deploy or maintain these components to integrate an application.

## Source map

The implementation checkout is `/home/dungxbuif/workspace/projects/RelayHub`.

- `rust/src/identity.rs`: workspace, application, session and credential authentication.
- `rust/src/events.rs`: event acceptance, idempotency and durable acceptance authority.
- `rust/src/delivery.rs`: leases, attempts, settlement, retry and dead-letter state.
- `rust/src/gateway.rs`: outbound agent WebSocket and durable delivery frames.
- `rust/src/webhooks.rs`: inbound endpoint policy, raw request handling and synchronous response rendezvous.
- `rust/src/realtime.rs`: ephemeral realtime channel behavior.
- `rust/src/host.rs`: runtime composition and migrations.
- `web/remake-admin/`: operator dashboard source.
- `deploy/production/`: staged runtime manifests; reconcile against the live inventory before applying.

## Runtime design

The service uses PostgreSQL on Pi5 as the authoritative store for identity, event acceptance, delivery state, audit and recovery metadata. NATS JetStream carries durable work signals, and Redis holds expiring presence and bounded realtime state. VM100 runs application compute. Private service DNS and the Pi5 file-provider ingress route internal services; no public docs should expose these names or topology.

Acceptance writes the event and outbox in one PostgreSQL transaction. A worker claims a delivery with a lease token. The receiver's acknowledgement is accepted only for the current lease generation. A lost acknowledgement can cause redelivery; application side effects must therefore use event IDs for deduplication. Replay creates a new generation and keeps the original audit trail.

## Operational controls

Keep application keys, agent credentials, transport credentials and encryption material in their documented secret stores. Do not place values in this document or in the public docs/skill/SDK archives. Verify PostgreSQL backup and restore before schema changes, keep the Databasus enrollment current, and record the exact deployed image/source revision in the vault.

This is an operator reference only. Do not link it from `llms.txt`, public Docusaurus navigation or customer-facing SDK instructions.
