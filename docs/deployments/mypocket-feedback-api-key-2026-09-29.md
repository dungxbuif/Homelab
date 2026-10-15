# MyPocket feedback API-key rollout (2026-09-29)

The feedback HTTP routes now accept owner-scoped user API keys in addition to
the existing session authentication:

- `feedback:read` for listing, reading, and screenshot retrieval.
- `feedback:write` for creating feedback; write keys also imply read access.

The API image was pushed to the private registry and rolled out to the Swarm
manager service:

- Image: `registry.dungxbuif.com/mypocket-api:feedback-api-20260929-215820`
- Digest: `sha256:7d4f3b46ece1b3dca1f8f7168f771a6afdffc9deef0b018cf173eed93739037`
- Service: `mypocket-api` (one replica on `vm100-prod`)

The overview timestamp fix was built and rolled out separately to the web
service:

- Image: `registry.dungxbuif.com/mypocket-web:feedback-ui-20260929-235423`
- Digest: `sha256:38e75ebc09534c31587aee59af49500aac62794c7821891480abc07667d60d93`

The AI-entry timeout regression was then rolled out as a second web image with
the Nginx API proxy read/send timeouts set to 240 seconds:

- Image: `registry.dungxbuif.com/mypocket-web:feedback-ui-ai-timeout-20260930-235918`
- Digest: `sha256:be887dcaf5abc20dc661f57267834418cb3ddd76e67a2ce87d793b298b81129e`

Verification after rollout:

- Swarm service converged to the new digest.
- Running container reports `healthy`.
- `https://money.dungxbuif.com/` returns HTTP 200.
- The public HTML references the new frontend bundle `index-CZJM4Ean.js`.
- The running Nginx config reports `proxy_read_timeout 240s` and
  `proxy_send_timeout 240s`.

The category-search ordering fix was rolled out as the current web image:

- Image: `registry.dungxbuif.com/mypocket-web:feedback-ui-search-20260930-000311`
- Digest: `sha256:b28c0c3b91dbdd75e3b0928361246d600a49af2213766b7114f267a6cdd95301`

The AI date/duplicate review fix was then rolled out as a new API image:

- Image: `registry.dungxbuif.com/mypocket-api:feedback-api-ai-date-20260930-0011`
- Digest: `sha256:698227ed3d9c1c5394954b48fe14a312c734a3faa86d5d15277e442200baaa99`
- The API normalizes recognized date-only values in the account timezone and merges
  exact duplicate proposals within one submission while retaining review questions.
- `/api/v1/health` returned HTTP 200 after convergence.

The authentication refresh-token fix was rolled out as the current pair:

- API: `registry.dungxbuif.com/mypocket-api:feedback-api-refresh-20260930-0041`
  (`sha256:a452dc22ffc2ce7809e36620b921337cfe422f9a7625d36e79692c1d9ced497e`)
- Web: `registry.dungxbuif.com/mypocket-web:feedback-ui-refresh-20260930-0032`
  (`sha256:b794c18962754f4e7379ab7f7d307e7579a4f9ab70fa632a71497cae4f164429`)
- `/api/v1/health` returned 200 and an invalid refresh token returned 401.
- Unauthenticated `GET /api/v1/feedback` is rejected with HTTP 401.

Production configuration contains the API-key hashing secret and feedback
agent token. Secret values are intentionally not recorded here. A user API key
must still be created by an authenticated owner before exercising the new
feedback scopes from a client.

The wallet-selector UI reconciliation was rolled out on 2026-09-30:

- Web: `registry.dungxbuif.com/mypocket-web:feedback-ui-wallet-design-20260930-0700`
  (`sha256:933dd62630e3ee5ae7917c6ddaab36b3d858bc58f2fdb0abb87cc2dd5e36d80e`)
- Swarm service `mypocket-web` converged successfully.
- Public HTML serves the new bundle (`index-DKFi4a4H.js` / `index-3IKszz6N.css`).
- `https://money.dungxbuif.com/api/v1/health` returned HTTP 200.
