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

## Path evidence and next verification contract

Unauthenticated HTTPS probes on 2026-10-15, with certificate validation and
explicit `--resolve`, from the LAN workstation:

| Endpoint | VPS 103.82.21.202 | Pi LAN 10.10.0.5 |
| --- | --- | --- |
| CouchDB | 401 | 401 |
| pgAdmin | 302 | 302 |
| Semaphore | TLS verification failed (curl 60) | 200 |

The VPS path reaches CouchDB/pgAdmin authentication; authentication is not a
network access restriction. This is a LAN-to-public-gateway test, not an
independent external-source test. Semaphore's TLS failure does not prove that
its private access boundary works. The CouchDB sync runbook explicitly expects
public clients, so its desired LAN-only catalog policy needs reconciliation
with those consumers before any publish. Do not cut off sync implicitly.

Implement a repeatable read-only `probe-route-paths.py`: validate the catalog,
probe every declared hostname/health path against a selected explicit gateway,
preserve TLS and SNI, disable curl config/proxies/redirects, send no credentials,
discard bodies/headers, and output only sanitized JSON status evidence. Network
errors, TLS failures and unknown HTTP results must remain incomplete, never
become a successful access-policy verdict. Do not run live probes automatically
from CI; CI covers request safety, alias coverage and failure classification.
This is endpoint evidence, not gRPC/WebSocket/authenticated application testing
or proof that a 403 came from the intended middleware. No public behavior changes.

Full probe of 24 catalog entries (26 hostname/path requests per gateway) found
incorrect health paths: RelayHub defines `/readyz` in
`backend/internal/httpapi/router.go`; MyPocket registers `/api/v1/health` through
`backend/internal/controller/http/router.go` and `routes_auth.go`. Correct those
catalog paths only after confirming both gateways return 200. Do not change
application code or redeploy these applications for a monitoring-path error.

Verified both corrected endpoints return HTTPS 200 on both gateway paths;
catalog paths are now corrected with regression coverage. Other observations
remain unresolved: LLM returns 502 on both paths (Mac-native development
exception, not restarted); Stirling returns 200 on LAN but curl 60 through VPS;
Semaphore and KubeKosh also have curl 60 through VPS, not a verified denial.
NetBird `/api` returns 404 and its gRPC catalog entry's `/` actually exercises
the dashboard; neither is evidence of API/gRPC health. RustFS root requests
return 403 without credentials; authenticated object operations were not tested.

Usage from the pinned execution environment:

```sh
python automation/scripts/probe-route-paths.py --address 10.10.0.5
python automation/scripts/probe-route-paths.py --address 103.82.21.202
```

Use repeated `--route ID` to narrow probes. JSONL is sanitized for a job
artifact. Exit 0 means all selected requests received an HTTP response with
valid TLS, including 4xx/5xx; it does NOT mean the services or access policy
passed. Exit 1 means transport evidence is incomplete; 2 is invalid input.
Every result explicitly carries `scope=endpoint_transport_only`.

Verification: six probe tests and the endpoint regression passed, with 66 tests
in the full automation Python suite and 24 rendered routes validated. The
corrected probe returned 200 for both applications through VPS. Focused review
found no blockers. No gateway files, services, credentials or public docs were
changed; this work adds operator evidence and corrects monitoring metadata.

## 2026-10-15 VPS certificate evidence

The full read-only route probe was repeated after the latest runtime changes.
The Pi5 LAN path completed transport for all 26 selected hostname/path requests.
The VPS path completed 23/26; the incomplete requests were:

| Hostname | Exposure in catalog | VPS result |
| --- | --- | --- |
| `stirling.dungxbuif.com` | public | TLS verification failed (curl 60) |
| `semaphore.dungxbuif.com` | LAN-only | TLS verification failed (curl 60) |
| `kubekosh.dungxbuif.com` | LAN-only | TLS verification failed (curl 60) |

An SNI-only OpenSSL check against `103.82.21.202:443` returned the Traefik
default certificate for all three names (`CN=TRAEFIK DEFAULT CERT`, verify
code 21). This is evidence that the VPS gateway does not currently select a
trusted certificate/route for these names; it is not evidence that the Pi5
backends are down. The LAN-only entries are expected to remain unavailable
from the public boundary. `stirling` is cataloged public and needs a controlled
VPS gateway certificate/HostSNI repair before it can be called healthy.

The VPS gateway is not editable through the current approved SSH credentials:
the pinned-key attempt for the documented `automation` route was rejected, and
no alternate credential was used. No VPS configuration or certificate was
changed. The next action is to repair the VPS `/root/gateway` certificate and
HostSNI entry through the approved VPS access path, then rerun the same probe.
Until then, do not mark `stirling` public TLS as verified and do not publish
the LAN-only routes at the public boundary.
