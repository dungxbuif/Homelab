# Retire `llm.dungxbuif.com`

## Intended behavior

The unused public LM Studio route is retired. `llm.dungxbuif.com` must no
longer be published by the Pi5 edge, and the Mac Rathole client dedicated to
that route must be removed. The wildcard DNS entry for `*.dungxbuif.com` is
not removed because it is shared by other services.

## Scope

- Remove the declarative `llm` route and `mac-llm` runtime dependency.
- Remove the generated and legacy Traefik router/service blocks for the LLM
  hostname.
- Remove the dedicated Mac `mac-service-tunnel` project and its runtime
  Rathole configuration.
- Remove the VPS Rathole listener/peer for port `18123` if present.
- Preserve the OCR route, NetBird relay/control plane, GitLab tunnels, and
  shared wildcard TLS/DNS configuration.

## Verification plan

1. Validate route rendering and route-contract tests.
2. Confirm no active source/config reference remains outside historical docs.
3. Confirm the Pi5 Traefik runtime no longer routes the hostname while OCR and
   NetBird remain healthy.
4. Confirm the Mac tunnel container/project and VPS `18123` listener are gone.
5. Record any gateway-side access limitation explicitly rather than claiming
   that listener removal was completed without evidence.

## Result

- Pi5 source and runtime Traefik no longer contain the LLM router/service; the
  edge was restarted to load the removal.
- The Mac-only `mac-service-tunnel` project was deleted after confirming it was
  dedicated to `mac-llm`.
- Gateway Rathole was recreated with the shared `7000` service and OCR
  `18087` service only; the `18123` listener is closed. The legacy firewall
  guard remains for OCR `18087` and no longer names `18123`.
- Shared wildcard DNS remains in place and `llm.dungxbuif.com` still resolves
  to the Pi5 wildcard address, but the hostname now returns HTTP 404.
- Verification: route-contract tests `13/13` passed; OCR health returned 200;
  NetBird OIDC discovery returned 200; the retired LLM route returned 404.
