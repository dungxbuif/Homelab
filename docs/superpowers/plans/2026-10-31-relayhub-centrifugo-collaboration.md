---
type: Plan
title: RelayHub Collaboration and Release Implementation Plan
generated:
  by: "process:vault-import"
  at: "2026-10-31T16:00:00+07:00"
stale_after: "2026-12-30T16:00:00+07:00"
---

# RelayHub Collaboration and Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add durable Yjs document synchronization and prepare a reproducible, verified release of the integrated fork stack.

**Architecture:** A private Node companion uses the existing Yjs engine for stateless merge/diff. The Go fork authorizes document operations and persists snapshots plus outbox events before acknowledgement; Centrifugo remains the public transport. SDK providers perform synchronization and ephemeral awareness; release automation verifies compatibility, restore and rollback.

**Tech Stack:** Yjs 13.6.30, y-protocols 1.0.7, lib0 0.2.117, Node 22+, Go 1.27.1, PostgreSQL, Centrifugo, Playwright, Docker/Swarm.

**Spec:** [Centrifugo fork design](../specs/2026-10-31-relayhub-centrifugo-fork-design.md). Prerequisites: [foundation](2026-10-31-relayhub-centrifugo-foundation.md) and [rooms](2026-10-31-relayhub-centrifugo-rooms.md). C1 can run independently once the contracts are agreed; C2 requires R1/R2, C3 requires C2, C4/C5 join all plans.

## Global Constraints

- Yjs companion dependencies start at `yjs@13.6.30`, `y-protocols@1.0.7`, and `lib0@0.2.117`, resolved in the pinned PartyKit lockfile.
- Document updates are at most 256 KiB; full snapshots at most 1 MiB; companion HTTP bodies at most 2 MiB and requests time out after 2 seconds.
- Awareness entries are at most 8 KiB, expire after 30 seconds and are never durable.
- Go exposes binary document operations, not a Yjs editing engine.
- New service listeners use client port 8000 and private API/admin/metrics port 9000, with no published host ports.
- Public route prefix is `/realtime`, stripped before forwarding `/connection/websocket`; deny public access to internal APIs. The Yjs companion is private on port 8090.
- PostgreSQL is authoritative on Pi5; no durable document files on VM100. Production secrets use Swarm secrets and documented 1Password mappings.
- Production activation remains a separate operator-authorized step. Local tests, packaging and a concrete rollout proposal are authorized implementation work; writing this plan changes no runtime.

## Review Focus

1. Offline concurrent edits and expired broker history must converge after full synchronization — C1/C3.
2. A malformed/oversize update or companion crash must not poison stored state or receive durable acknowledgement — C1/C2.
3. Lost acknowledgement, repeated update ID and outbox replay must preserve one accepted version — C2/C3.
4. Awareness from a disconnected client must expire and cannot impersonate another tenant — C3.
5. A fresh clone, backup restore or rollback must work without ignored local files or missing fork commits — C4/C5.

---

## File map and interfaces

Source paths are relative to `/home/dungxbuif/workspace/projects/RelayHub` unless explicitly under `homelab-ops` or the vault.

| Files | Responsibility |
|---|---|
| `third_party/centrifugo/extensions/collaboration/{package.json,package-lock.json,src/engine.ts,src/server.ts,test/engine.test.ts,Dockerfile}` | Private bounded Yjs merge/diff service |
| `third_party/centrifugo/internal/relayhub/documents/{engine.go,store.go,rpc.go,migrations/0001_documents.sql}` and matching tests | Document authorization, durable snapshot CAS, outbox |
| `third_party/centrifuge-js/src/{documents.ts,documents.test.ts}`; `third_party/centrifuge-go/{documents.go,documents_test.go}` | Yjs provider and binary document APIs |
| `tests/realtime/{documents.test.mjs,documents.spec.ts,fixtures/reference-yjs.mjs}` | Independent convergence and failure tests |
| `scripts/{realtime-release.sh,verify-realtime-release.mjs}`, `deploy/realtime/{compose.yaml,centrifugo.json}`, `.github/workflows/realtime-compat.yml` | Reproducible artifacts and CI gates |
| `homelab-ops/automation/stacks/relayhub-realtime/{stack.yml,centrifugo.json}`, route catalog/tests | Portless deployment proposal, secret references and ingress |
| Vault `docs/services/relayhub-realtime.md` | Deployment evidence, secret mappings, backup and rollback procedure |

`DocKey = {workspace_id,app_id,room,document}`; client requests never supply workspace/app. Document IDs follow room ID byte limits. Binary values use canonical padded base64 in JSON, bytes inside SDK engines; reject invalid base64. `DocSnapshot = {version:string, update:string, state_vector:string}`; `DocUpdate = {id:string,update:string}`; `DocReceipt = {version:string,replayed:boolean}`. UUID update IDs use durable deduplication like room commands, but Yjs merges may retry CAS up to three times because merge is pure; exhaustion returns `unavailable` and callers retry the same ID.

RPCs: `relayhub.docs.v1.sync` takes `{room,document,state_vector}` and returns `RpcOutcome<DocSnapshot>` containing the missing update; `.update` takes `{room,document,id,update}` and returns `RpcOutcome<DocReceipt>`; `.awareness` carries `{room,document,client_id,clock,state}` where `state` is a JSON object or null. Awareness clocks are nonnegative safe integers, strictly increase for changes within a connection generation and follow the existing y-protocols rules; heartbeat refresh runs every 10 seconds. Document publication channel is derived server-side from authorized room channel plus encoded document ID, with exact subscription-token policy extended in F2/F3. No raw client publication to document channels.

### Task C1: Prove the existing Yjs engine in a bounded companion

**Files:** Create companion files in the map, plus `tsconfig.json`, `test/server.test.ts`, `.dockerignore`; create parent `tests/realtime/fixtures/reference-yjs.mjs` and extend realtime contract fixtures.

**Interfaces:** `merge(snapshot:Uint8Array, update:Uint8Array):{snapshot:Uint8Array,stateVector:Uint8Array}` and `diff(snapshot:Uint8Array,stateVector:Uint8Array):Uint8Array`. Private `POST /v1/merge` accepts `{snapshot,update}` and returns `{snapshot,state_vector}`; `/v1/diff` accepts `{snapshot,state_vector}` and returns `{update}`. HTTP payload fields are base64. Require a service bearer secret, never a user grant.

- [ ] Write `concurrent_offline_updates_converge`: use two independent `Y.Doc`s, edit offline, apply updates in both orders and with duplicates, then assert identical `toJSON()` and state vectors after merge/restore. Feed updates produced by the pinned reference Yjs package. Assert malformed base64, invalid Yjs bytes, 256 KiB + 1 update and 1 MiB + 1 result reject without partial output; a forged bearer is `401`.
- [ ] Run in companion `npm test`; expect FAIL for missing implementation. This is the bounded engine proof: if reference convergence/resource tests fail, report that evidence before choosing another engine; do not write a new CRDT.
- [ ] Implement the signatures with `Y.applyUpdate`, `Y.encodeStateAsUpdate`, `Y.encodeStateVector`. Run processing in a worker thread per bounded job pool (maximum four concurrent jobs, no unbounded queue); terminate jobs exceeding 2 seconds and release `Y.Doc`s. HTTP handlers enforce decoded limits as well as the 2 MiB encoded body cap. Container memory limit is 256 MiB; no file persistence. Preserve dependency licenses in the built artifact.
- [ ] Run `npm test` and the service integration tests inside its constrained container; expect PASS, timeout leaves the next valid request usable, restart restores no accidental in-memory state. Record image digest, dependency lock hash and convergence results before Go integration.
- [ ] Commit only in the server fork `git commit -m "feat: add bounded Yjs merge companion"`; commit reference fixture/schema separately in the parent.

### Task C2: Persist accepted document changes before replying

**Files:** Create server `internal/relayhub/documents/{engine.go,engine_test.go,store.go,store_test.go,rpc.go,rpc_test.go,migrations/0001_documents.sql}`; modify fork config/runtime/discovery and R2 outbox routing; create parent `tests/realtime/documents.test.mjs`.

**Interfaces:** `Engine.Merge(ctx context.Context,snapshot,update []byte)(snapshotOut,stateVector []byte,err error)`, `Engine.Diff(ctx context.Context,snapshot,stateVector []byte)([]byte,error)` consume C1. `Store.Apply(ctx context.Context,key Key,id string,update []byte)(Receipt,error)` and `Store.Sync(ctx context.Context,key Key,stateVector []byte)(Snapshot,error)`; document `Key`, `Receipt`, `Snapshot` map to the wire contract above. Scope comes from `authz.Scope`; write/read use the same room authorization as R2. Document event `{id,document,version,update}` uses R2 outbox worker through a typed destination/payload field, not a room-state cast.

- [ ] Write `TestDocumentDurableAck`: stop PostgreSQL before commit and assert no success receipt; stop the process after commit before reply and retry the same ID, asserting one version and `replayed=true`. Different bytes under one ID conflict. Concurrent updates from two replicas converge; companion timeout leaves snapshot/outbox unchanged. Drop broker history and restart every server, then assert full sync reconstructs the reference document. Reject cross-workspace document keys.
- [ ] Run `GOWORK=off go test -race ./internal/relayhub/documents`; expect FAIL for missing implementation.
- [ ] Implement snapshot read → pure engine merge outside transaction → CAS plus dedup/outbox commit. Retry a stale CAS at most three times; check durable dedup before and after races. Store the merged snapshot, state vector and version atomically; each accepted command replaces the full snapshot, so there is no unbounded separate document update journal to compact. Outbox retains events only through R2's delivery/retention policy; backup uses the current authoritative snapshot and command records. Emit no durable success until commit returns. Extend session requests with optional document subscriptions `{room,document,access}` and bind them to the same scope checks; do not grant wildcard access through channel spelling.
- [ ] Run Go tests plus F1 `--suite documents --server fork --case engine-store`; expect PASS. Exercise two replicas, broker restart and snapshot serialization round-trip. Keep `documents:0` until the provider/awareness task is ready.
- [ ] Commit server and parent fixtures separately with `feat: persist and synchronize collaborative documents`.

### Task C3: Provide SDK synchronization, awareness and dashboard verification

**Files:** Create JS `src/{documents.ts,documents.test.ts}`, Go `documents.go`, `documents_test.go`; update fork exports/package manifests and product wrappers. Create parent `tests/realtime/documents.spec.ts`; extend `web/remake-admin/src/RealtimeStudio.tsx`, add `web/remake-admin/tests/collaboration.spec.ts`; add server `documents/{awareness.go,awareness_test.go}`.

**Interfaces:** JS `RelayHubRealtime.document(room:string,id:string,doc:Y.Doc):RelayHubYProvider`; provider exposes `connect():Promise<void>`, `destroy():void`, `awareness:Awareness`, `synced:boolean` and `on("synced"|"error",listener)`. Use the existing `y-protocols/awareness` model, with server validation/binding. Go `(*RelayHub).Document(room,id string)*Document`, `Sync(ctx,stateVector []byte)(DocSnapshot,error)`, `Update(ctx,id string,update []byte)(DocReceipt,error)`; Go is a binary transport API, with no promise of local CRDT editing. JS/Go doc event subscription exposes validated binary updates.

- [ ] Write `provider_converges_after_offline_history_loss`: two real browser clients edit, disconnect one, expire history, reconnect, and assert identical reference state. Assert subscribe-before-sync covers concurrent updates, dropped ACK resends the same UUID, own publications cause no feedback loop and destroy releases listeners. Awareness spoofing across connections/tenants fails; disconnect/crash expires its state after 30 seconds; 8 KiB + 1 rejects. A Go client uploads a reference binary update that the browser can read.
- [ ] Run fork SDK tests and browser collaboration tests; expect FAIL for missing provider/awareness integration.
- [ ] Implement provider subscriptions before initial state-vector sync, with buffered publications and Yjs idempotent application. Track local unsent changes in memory until acknowledged; on reconnect coalesce missing edits from the live `Y.Doc` after state-vector exchange. Do not promise survival of browser closure without an explicitly configured local persistence provider. Bound queued updates to 256 KiB; on overflow mark unsynced, discard the redundant queue and perform state-vector sync from the local document, rejecting documents over 1 MiB with a clear error. Awareness client IDs are bound to authenticated connection generations; reject a second connection claiming an active ID and permit rebind only after expiry/disconnect. Persist no awareness state. Use existing Yjs peer dependencies to avoid duplicate engine instances.
- [ ] Run complete document suite, browser typecheck/build/Playwright, SDK tests and baseline matrix; expect PASS. Set `documents:1` only after every advertised RPC/provider feature passes. Show convergence in a small dashboard test panel, not a full new editor product. Clear ephemeral awareness on teardown and verify it is absent after restore.
- [ ] Commit each repo's owned files with `feat: expose collaborative documents and awareness`.

### Task C4: Publish recoverable fork sources and verify release artifacts

**Files:** Create parent `scripts/{realtime-release.sh,verify-realtime-release.mjs}`, `.github/workflows/realtime-compat.yml`, `deploy/realtime/{compose.yaml,centrifugo.json}`; modify `third_party/{README.md,upstreams.lock.json}`. Artifact output goes to ignored `dist/realtime/`. Fork Dockerfiles/build scripts and SDK manifests change only as required for their own artifacts.

**Interfaces:** `scripts/realtime-release.sh --version VERSION --output DIR` produces `release.json`, SHA256 sums, JS package tarballs, Go source archive, server/companion image references and a runnable disposable Compose bundle. `release.json` records component versions, owned source remotes/commits, upstream bases, image digests, protocol feature versions and compatibility-report hash. `node scripts/verify-realtime-release.mjs DIR` fails on missing/unreachable pins or checksum mismatch; it does not infer test success from package existence.

This complete release bundle and provenance manifest are internal operator artifacts. Public docs/Developer Kit receive only the allowlisted client SDK/CLI/skill projection defined by D3 of the [product docs plan](2026-10-31-relayhub-product-docs.md); do not copy backend sources, engine names, images, Compose configuration or private source mappings into public downloads. Keep necessary client dependency licenses/build metadata intact.

- [ ] Write verifier tests: deleting one fork remote commit, altering one package byte or omitting one matrix cell makes verification fail; a fresh checkout restores every pinned source without local ignored trees. Test building/installing JS tarballs and compiling the Go SDK from the released source/module, not only monorepo links. Include licenses and exclude secrets, caches, `node_modules` and `.git`.
- [ ] Run verifier on an intentionally incomplete fixture; expect FAIL with the missing source/artifact identified.
- [ ] Create owned private GitHub/GitLab repositories for server/SDK forks after checking existing repositories; proposed names are `dungxbuif/centrifugo`, `dungxbuif/centrifuge-js`, `dungxbuif/centrifuge-go`. Do not overwrite an existing unrelated repo or push to upstream. Push each fork branch to both owned remotes and verify commit IDs, then update parent `checkout_commit`/`fork_remotes`; keep upstream base pins unchanged. Record a registry source for the Go module that consumers can authenticate to; do not claim an unauthenticated public install for a private repo. Pack experimental SDKs without publishing public package names unless explicitly requested. Build amd64 runtime images with immutable digests; add arm64 if a component is assigned to Pi5. Preserve the default-deny Docker context by building each nested repo from its own root.
- [ ] Run upstream test suites unchanged plus `scripts/realtime-compat.sh --suite all --server both --report dist/realtime/compatibility.json`; expect PASS, zero missing cells and verifier exit zero. Require all JSON/Protobuf browser/Node/Go combinations, auth, legacy durable, room and document fault cases. Run packaging/verifier from a clean temporary checkout and restore the database into an isolated cluster; assert room version/state, pending alarm identity and Yjs state vectors match backup. Record actual results and resource measurements; no skipped required cells or floating `latest` artifacts. For future upgrades add the previous supported baseline to the same matrix.
- [ ] Commit fork build changes first, push/verify them, then commit/push parent lock and release automation on feature branches. `git commit -m "build: package verified realtime fork release"`. No main merge or production activation is implied.

### Task C5: Prepare the portless deployment, backup and rollback change

**Files:** In `/home/dungxbuif/workspace/projects/homelab-ops`, create `automation/stacks/relayhub-realtime/{stack.yml,centrifugo.json}`, `automation/tests/test_relayhub_realtime.py`; modify `automation/routes/catalog.yml` and regenerate `automation/routes/generated/pi5-traefik.yml` using its existing publisher. In the vault create `docs/services/relayhub-realtime.md`. Preserve unrelated dirty files in all repos.

**Interfaces:** Consumes verified C4 `release.json`; produces a reviewed Swarm manifest, file-provider ingress diff and runbook with artifact digest, secret mapping, dedicated DB/role, backup enrollment, restore evidence, canary acceptance and rollback commands. New service DNS names: `relayhub-centrifugo` and `relayhub-yjs`; actual networks must be reconciled against live inventory before applying.

- [ ] Write `test_realtime_network_boundary`: assert no published host ports; client ingress reaches only `/realtime/connection/websocket`; public `/realtime/api`, `/internal/realtime/v1/authorize`, admin and metrics do not route to private handlers; companion has no public route. Assert immutable image digests, Swarm secret mounts and no plaintext credentials. Run the existing route contract tests too.
- [ ] Run `python3 -m unittest discover -s automation/tests -p '*relayhub_realtime*'`; expect FAIL until manifests/policy are implemented. Inspect the existing route publication/test conventions before wiring generation, rather than inventing a second publisher.
- [ ] Implement the manifests and route policy. Mount private API/JWT/policy/companion credentials as distinct secret references with explicit runtime `_FILE` loading/validation; private-network placement alone is not authentication. Set resource limits and health checks; separate client/internal listeners. Plan a dedicated Pi5 `relayhub_realtime` database/user and follow `creating-postgres-databasus-backup` during authorized provisioning, including an observed successful backup and Drive-folder verification. Do not mutate production merely to validate this task. Document exact 1Password vault/item/field ↔ service/variable mapping, without values. New room/doc state is absent from the old backend, so rollback disables the new entry point while preserving the new database; never drop schemas or pretend old binaries can read it.
- [ ] Run manifest/route checks and a disposable deployment using the same image/config bundle; expect unittest `OK`, acceptance PASS and no exposed private endpoint. Exercise authenticated browser/Go/Node connect, revoked token, room mutation, alarm restart, document convergence, private-endpoint denial and restore. Write an operator-ready canary procedure: dedicated app/tenant first, compare observed errors/latency/resource use with the verified disposable run, stop on any auth/state/restore failure, then promote only with recorded approval. Capture actual evidence after authorized activation; before that label status `prepared, not deployed`.
- [ ] Commit/push only owned ops/runbook changes on feature branches: `git commit -m "ops: prepare realtime deployment and recovery runbook"`. Present the exact rollout diff and remaining operator action; do not silently restart existing production services.

## Handoff and verification record

This plan does not claim convergence, backup, runtime compatibility or deployment has been verified yet. Main-agent self-review assigns CRDT correctness to C1/C2/C3, whole-product compatibility and source recovery to C4, and infrastructure/restore/rollback to C5. Product Docusaurus, machine-readable docs, downloadable skills and SDK Developer Kit are a separate requested workstream; they consume the release manifest and must label planned features accurately.
