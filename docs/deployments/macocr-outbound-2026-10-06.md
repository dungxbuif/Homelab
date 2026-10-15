# MacOCR outbound Mac worker release — 2026-10-06

## Proxy rollout — 2026-10-08

- Source: current `codex/macocr-outbound-nodes` worktree at deployment time; no native app rebuild or restart.
- Swarm image: `homelab/macocr-proxy:scan-api-20261008`.
- Service: one `macocr-proxy` task constrained to `vm100-prod`; existing secrets, healthcheck, `homelab-net`, `edge-http-net`, and `ocr.dungxbuif.com` routing were preserved.
- Verification: Go tests `121/121`, `go vet`, service convergence, container health/readiness, public HTTPS health/readiness, root docs, and runtime OpenAPI scan paths passed.
- Public anonymous scan submission correctly returns `401`. Authenticated scan E2E remains pending a currently active API key; the stale local credential was not rotated as part of this rollout.

## Capacity follow-up

The follow-up worker build disables adaptive CPU/memory/thermal gating by default.
This prevents transient macOS memory readings from removing all capacity from
the worker roster. Operators can opt into the adaptive policy with
`MACOCR_ADAPTIVE_CONCURRENCY=true` and tune its reserve values when needed.

The resulting Universal app is version `2.0.0`, build `9`; it embeds
`MacOCRAdaptiveConcurrency=false` and keeps the adaptive reserve values only as
an opt-in configuration.

## Deployed state

- Source branch: `codex/macocr-outbound-nodes`
- Source commit: `8d1f951`
- Swarm image: `homelab/macocr-proxy:activate-20261006`
- Public endpoint: `https://ocr.dungxbuif.com`
- Native transport: outbound WSS/443 with shared-key authentication and stable per-host fingerprints
- Proxy replicas: one socket-owning replica
- Worker control: admin `Activate` clears a deliberate revoke while preserving node identity and credentials; shared-key workers reconnect automatically after activation.

The Mac no longer exposes an OCR listener and the OCR Rathole mapping remains removed. The LLM tunnel is unchanged. The old per-user installation was removed, and the operator installed the final DMG manually at `/Applications/Mac OCR Native.app`. Dashboard verification shows the production node connected and `Ready` with expanded machine metadata and one effective status.

## Manual artifacts

- App: `/Users/dungxbuif/workspace/mac-ocr/native/dist/Mac OCR Native.app`
- DMG: `/Users/dungxbuif/workspace/mac-ocr/native/dist/Mac-OCR-Native-2.0.0-universal.dmg`
- ZIP: `/Users/dungxbuif/workspace/mac-ocr/native/dist/Mac-OCR-Native-2.0.0-universal.zip`

The binary is ad-hoc signed and Universal (`arm64`, `x86_64`) with macOS 13 as its minimum system. Apple Silicon was accepted on physical hardware; the Intel slice was build/signature verified without a physical Intel acceptance machine.

## Administration and verification

Admin SPA routes are `/admin/users`, `/admin/workers`, and `/admin/api-keys`; direct load, refresh, and browser history are supported. Machine metadata is always visible on the protected Workers page, which shows one effective node status. Both User Management and Mac Workers & Routing use server-side administrator authorization in addition to role-gated navigation.

Verification passed for Go tests/vet, native Swift capacity/socket/controller suites, React and Docusaurus production builds, Universal architecture and strict ad-hoc signature checks, production health, direct admin route loads, anonymous API rejection, rate-limit boundaries, and production image/PDF/scan routing through the outbound Mac worker. Durable Pause/Drain/Resume settings persist in PostgreSQL across reconnects and proxy restarts.

The final docs-only image publishes the human install guide and release notes plus the stable agent-readable worker protocol. Live checks confirmed the artifact names, build 7/macOS support statement, and admin route catalog from the public domain.

Test-account cleanup removed `ocr-bench-20260923150429@local.invalid`, `outbound-smoke-20261006@macocr.test`, and `developer@dungxbuif.com`, including associated database/cache/object resources. PostgreSQL confirms `huy.buidoanquang@mezon.ai` has role `admin`; the account must sign in again to receive a new role-bearing session.
