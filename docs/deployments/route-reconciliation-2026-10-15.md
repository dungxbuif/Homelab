# Route reconciliation before automation publish

Read-only inspection of Pi's mounted Traefik dynamic file on 2026-10-15:
`/home/dungxbuif/edge/traefik/dynamic.yml` -> `/etc/traefik/dynamic.yml`.
Only router rules/middleware/service references and backend scheme/host/port
were collected; no TLS secrets, auth material or full environment was printed.

The live file has 24 HTTP routers; the automation catalog has 21. Missing
catalog entries are Semaphore (LAN-only, tasks.semaphore_semaphore:3000),
KubeKosh (LAN-only, kubekosh:80), and k8s-syntax (public, tasks.k8s-syntax:80).
LLM live backend is `http://103.82.21.202:18123`, not direct Mac port 1234.
Record it as the observed tunnel backend, without changing the live service.

Important unresolved policy drift: live CouchDB and pgAdmin routers have no
LAN middleware, whereas the catalog declares them LAN-only. This alone does
not prove internet reachability through the VPS boundary, but applying the
catalog would change access policy and could disrupt existing consumers.
Do not resolve this by silently broadening the desired policy or publishing it.
NetBird backend service IDs also differ, although endpoints match.

Update missing catalog entries and LLM's observed tunnel, add regression tests,
and keep route publication pending until complete router/middleware/TLS/VPS
comparison and consumer acceptance. No live route/network changes. Public app
docs are unchanged because public behavior is unchanged.

Additional renderer audit findings before the corrections below:
- Accepted `netbird`/`internal` exposure modes currently render an unprotected
  router. Explicit private semantics must be enforced, not treated as public.
- The JSON schema disallows the existing top-level catalog_name/middlewares
  fields; the renderer currently does not invoke that schema.
These are source readiness gaps, not evidence of a deployed routing incident.

Correction contract: validate the actual catalog against its JSON schema on
every render; declare existing metadata/middleware fields in that schema.
Internal routes produce no edge router/service. NetBird routes require a
dedicated netbird-only IP allowlist, LAN routes require lan-only, and those
allowlists accept only explicit RFC1918/CGNAT/ULA subnets, never an empty or
public catch-all. Reject public Semaphore routes and unsafe generated hostnames.
Pin the already installed jsonschema 4.26.0 dependency explicitly in the
execution environment. Existing public/LAN output must remain deterministic.

Implemented and verified: catalog now contains 24 routers, preserving desired
LAN restrictions for CouchDB/pgAdmin rather than silently accepting live drift.
The renderer invokes schema validation, omits internal routers/services, and
requires a dedicated private allowlist for NetBird routes. Schema now describes
existing metadata/middlewares and rejects unsafe generated hostnames. Public
Semaphore targets are rejected. No live file was modified.

Review found a configuration combination that could rewrite X-Forwarded-For
before an allowlist using ipStrategy.depth. Traefik documents that depth selects
from that header: [IPAllowList reference](https://doc.traefik.io/traefik/reference/routing-configuration/http/middlewares/ipallowlist/).
The fix allows only `ipAllowList.sourceRange` for mandatory private gates and
places the gate before route-supplied middleware, deduplicated. This does not
replace validation of trusted-proxy/source-address behavior through VPS/Rathole.

Twelve route tests pass, including reproduced schema/exposure/forwarded-header
failures and malformed allowlists. The full automation Python suite passes 59
tests; `verify-routes.sh` validates all 24 rendered routes. Final focused review
has no remaining blockers. Route publication still requires live topology and
access-policy acceptance; passing generator tests is not deployment approval.
