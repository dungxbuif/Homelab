# NetBird and Homelab Automation

## Decision Summary

Status: proposed architecture, not deployed. Evidence baseline: repository configuration and official documentation reviewed on 2026-09-13; NetBird release baseline v0.78.1. Repository observations below are not a fresh audit of running containers. Live capacity remains unverified because SSH authentication failed.

Keep the existing public Traefik/Rathole path while adding private connectivity and controlled automation. Place NetBird management and Semaphore UI on VM100, external NetBird relay/STUN on the VPS, and all application databases on Pi5. Do not revive the retired NetBird configuration wholesale or introduce Pangolin alongside this initial deployment.

This is a dependency and ownership decision, not a conclusion that the VPS lacks capacity. A VPS-hosted management server is technically possible. However, reaching its Pi5 database through the very NetBird system it manages would introduce a bootstrap dependency. An independent private database transport would solve that problem but add another infrastructure path to maintain.

The deployment model should be Git-backed service declarations executed through Semaphore and Ansible. Semaphore is the operator interface, not a second source of configuration truth. Every change must have a visible plan, a controlled apply operation, verification, and a recovery path.

## Placement

| Host | Proposed responsibility | Boundary |
|---|---|---|
| VPS | Existing public Traefik and Rathole; new external NetBird relay/STUN | No application database or general app workloads |
| Orange Pi | Existing edge Traefik and local DNS | Public and private routing must be explicitly separated |
| VM100 | NetBird management/signal/dashboard, Semaphore, automation execution, database-access connector | Build workloads run here, not on Pi5 |
| Pi5 | PostgreSQL and other existing datastores | All NetBird and Semaphore databases stay here |
| External machines | NetBird peers or a containerized application-specific connector | Only approved resources, not unrestricted LAN access |

NetBird documents external relays with embedded STUN, so a separate Coturn installation is not a prerequisite for this design. Reserve public UDP 3478 for STUN and a TLS relay hostname using existing TCP 443 ingress; validate the selected relay transport before opening firewall rules. Do not install another proxy competing for host ports 80/443. [External relay documentation](https://docs.netbird.io/selfhosted/maintenance/scaling/set-up-external-relays)

The management endpoint must be reachable for initial enrollment without requiring an already working NetBird connection. Route its necessary API, identity, gRPC and WebSocket endpoints through the existing independent public ingress. Administrative access to the dashboard should remain restricted. Preserve the upstream HTTP/2 cleartext handling required by the gRPC routes. [Deployment configuration](https://docs.netbird.io/selfhosted/maintenance/configuration-files)

Configure all three NetBird persistent stores for PostgreSQL: management, activity events, and embedded identity. Moving only the primary store would leave SQLite state behind. Use distinct databases and restricted roles on Pi5, plus a separate Semaphore database. Back up encryption keys and configuration alongside database backups; they are necessary to recover encrypted state. The pinned configuration example and implementation support these stores. [Pinned example](https://github.com/netbirdio/netbird/blob/v0.78.1/combined/config.yaml.example), [pinned implementation](https://github.com/netbirdio/netbird/blob/v0.78.1/combined/cmd/config.go)

Prefer direct PostgreSQL service connectivity over a dedicated private Docker network for these control-plane databases initially. Do not assume every component's migrations and connection behavior are compatible with the existing PgBouncer pooling mode; test that separately.

### Availability Tradeoff

VM100 or Pi5 failure can prevent new enrollment and management operations. Existing peer connectivity must not be treated as guaranteed through every restart, expiration, or network change. This architecture deliberately accepts a local control-plane dependency in exchange for a simple private database path.

If remote-access administration must survive a total lab outage, revisit an independently hosted control plane. Keeping every database on Pi5 and expecting full control-plane independence from Pi5 are conflicting availability goals. Preserve a documented SSH/console recovery route that does not depend on Semaphore or NetBird.

## Existing Configuration Findings

These findings identify concrete automation hazards in the repository. They do not prove an equivalent live vulnerability or outage.

| Evidence | Finding | Recommended treatment |
|---|---|---|
| `edge-registrar/scripts/edge-publish.sh` | Domain publication still targets retired Pi5 Caddy paths and container names | Do not expose this script as a Semaphore job; replace it and archive it after validation |
| `iac/ansible/site.yml` | Main playbook provisions Kubernetes, including kube-vip and control-plane roles | Build a separate active Swarm automation entry point; retain the old tree as historical material |
| `migration/traefik/traefik.yml` | Only file provider is declared | Swarm membership alone does not make service labels create routes |
| `migration/traefik/dynamic.yml` | Several upstreams still use host IPs and published ports | Migrate eligible container workloads to stable service DNS, one app at a time |
| `migration/traefik/traefik.yml` | PROXY protocol trust covers broad private ranges | Discover actual upstream addresses and narrow trust; do not edit blindly |
| `migration/edge-stack.yml` | Mutable image tags and a node-local Rathole image; no per-service resource budgets declared | Pin tested images, publish reproducible multi-architecture artifacts where needed, set measured budgets |
| `docs/INDEX.md`, `docs/VM100.md` | Historical descriptions coexist with newer deployment details | Reconcile against verified runtime inventory and preserve superseded sections in history |

Start with generated Traefik file configuration because it matches the inspected source. A later Swarm-provider migration is reasonable, but should be a distinct change with access to the manager API carefully constrained. Never expose unauthenticated Docker TCP 2375. Do not let both a generated file and labels own the same route.

For file-provider updates, validate the rendered configuration and its reload behavior. Existing individual-file bind mounts need care when replacing files atomically; choose and test the mount/update mechanism before automation relies on hot reload.

The desired standard is service DNS for container backends, while stable infrastructure addresses remain valid in inventory, firewall rules, and bootstrap connectivity. Native Mac OCR and intentionally excluded development workloads are exceptions, not grounds for inventing container names that cannot resolve.

## Private Database Access

NetBird can provide policy-controlled access to specific network resources through a routing peer; the database host does not need to run a NetBird agent. Use a dedicated VM100 connector attached to a proposed private data-access overlay with the required database endpoint. This keeps networking-control workloads off Pi5. Resource domains must resolve from that connector, and access policies should permit only required destinations and ports. [Networks](https://docs.netbird.io/manage/networks), [routing peer behavior](https://docs.netbird.io/manage/networks/how-routing-peers-work)

An intended external application path is:

```text
Application container
  -> private connector endpoint
  -> NetBird encrypted connection, direct or relayed
  -> VM100 database-access connector
  -> PgBouncer service DNS
  -> PostgreSQL on Pi5
```

Do not advertise the entire LAN or all of `homelab-net` just to reach PostgreSQL. Existing applications within Swarm should continue to use their private overlay directly; they do not need an additional NetBird peer each.

Network policy distinguishes peers, destinations, protocols and ports. It does not distinguish PostgreSQL databases that share the same listener. Each project therefore needs its own database role and grants, with broad default cross-database privileges reviewed. A permitted TCP connection is not authorization to every database. Where attribution matters, remember that routed traffic commonly uses source NAT; preserve database-level identity and consider PostgreSQL TLS for the connector-to-database segment.

### Container Boundary

Putting an application and NetBird in separate containers on the same Docker network does not automatically route the application's traffic through NetBird. Two implementation candidates need a pilot:

1. A Compose application sharing the NetBird network namespace, with compatible privilege and interface setup.
2. An application-specific tunnel container exposing an ordinary internal TCP forwarding endpoint to its sibling application, without publishing it on the host.

The second option fits the desired `db-tunnel:5432` application experience but requires an additional forwarding component; it is a proposed wrapper, not a built-in generic NetBird database command. Compose namespace-sharing examples should not be copied directly into Swarm without validating deployment support. Rootless NetBird has outbound connectivity limitations, including reliance on SOCKS for that use case, which ordinary PostgreSQL clients do not automatically use. [NetBird Docker installation](https://docs.netbird.io/get-started/install/docker), [Compose service reference](https://docs.docker.com/reference/compose-file/services/)

For unattended enrollment, use short-lived or single-use setup keys scoped to a project group. Keep peer state distinct and persistent when identity must survive a restart. Revoking a setup key does not remove peers already registered with it; offboarding must revoke the peer or policy separately. Database sessions may also require termination for immediate access removal. [Setup keys](https://docs.netbird.io/manage/peers/register-machines-using-setup-keys)

## Service Catalog and Domain Ownership

Introduce an explicit, validated service catalog in Git. The following is a proposed schema example, not executable configuration:

```yaml
id: example-app
placement: vm100
image: registry.example.internal/example-app@sha256:REPLACE_WITH_DIGEST
exposure:
  mode: private
  hostname: example-app.internal.dungxbuif.com
backend:
  service: example-app
  port: 3000
database:
  binding: example-app
  endpoint: pgbouncer
  secret_ref: example-app-db-v1
access:
  groups: [project-example-app]
backup:
  policy: daily
```

The catalog owns route intent, backend service identity, deployment placement, database binding, access groups, and retention class. Secrets are references only. Generate deployment inputs, DNS records, routes, access policy and inventory documentation from this source. A manual emergency change must be reconciled back to Git, not silently overwritten later.

| Request | Generated changes | Required verification |
|---|---|---|
| Public domain | Cloudflare record, approved public ingress route, edge backend, TLS | HTTPS externally, correct app, no unintended admin endpoint |
| Private web domain | Private DNS, private listener, NetBird policy, backend | Authorized peer succeeds; unauthorized peer and public Internet fail |
| Private DB binding | Resource endpoint, peer group policy, secret reference | Correct database works; cross-project database access fails |
| Retire service | Withdraw access and routes, stop workload, preserve data by default | Route absent, peer access revoked, restore material retained |

Private DNS is not access control. A caller can send a private hostname directly to the public IP using Host/SNI. Private HTTP services therefore need a genuinely isolated ingress or enforced access boundary, not merely the absence of a public DNS record. NetBird custom zones can distribute private records by group, but are not Docker discovery or a substitute for network enforcement. [Custom DNS zones](https://docs.netbird.io/manage/dns/custom-zones)

Use structured Cloudflare DNS modules rather than shell text edits. Keep public DNS and private resolver records under separate explicit ownership to avoid conflicting A, AAAA, wildcard and split-DNS behavior. [Cloudflare DNS module](https://docs.ansible.com/projects/ansible/latest/collections/community/general/cloudflare_dns_module.html)

## Semaphore and Ansible Operating Model

Run Semaphore on VM100 with a PostgreSQL database on Pi5. Pin the execution image and Ansible collection versions. Limit its SSH identities, API credentials, inventory targets and accessible repositories. Protect the UI as a private administrative service and enable finite job-log retention.

Semaphore supports reusable task templates and survey variables suitable for forms such as service, image version, hostname and exposure mode. Community local execution is sufficient to begin; do not assume isolated per-task Docker execution or advanced workflow features are included. The documented Docker executor is a Pro feature. One reviewed Ansible playbook can orchestrate a multi-stage job without purchasing workflow functionality. [Task templates](https://semaphoreui.com/docs/user-guide/task-templates), [survey variables](https://semaphoreui.com/docs/user-guide/task-templates/survey-vars)

Use an explicit two-stage operator workflow:

1. **Plan:** validate catalog input, render proposed files, compare deployed state, detect conflicts, identify destructive operations, and show the exact Git revision and image digest.
2. **Apply:** run the approved revision with validated inputs, snapshot affected configuration, deploy, verify routing and access, and record the resulting revision.

Approval is not merely another free-form variable. Bind apply to the reviewed revision and inputs, reject unexpected drift, and serialize jobs touching shared DNS, ingress, or database state. Use separate permissions or projects for destructive workflows where the available role model cannot scope individual templates adequately. [Semaphore team permissions](https://semaphoreui.com/docs/user-guide/team)

Ansible check mode cannot be promised as a universal deployment preview: `community.docker.docker_stack` declares neither check-mode nor diff-mode support. Build the plan from rendering and explicit inspection instead of reporting unsupported dry-runs as successful checks. [Docker stack module](https://docs.ansible.com/projects/ansible/latest/collections/community/docker/docker_stack_module.html)

NetBird has an Ansible collection for API resources such as peers, groups, policies and DNS. Server installation and host/container setup remain separate automation responsibilities. Use an administrative API credential for resource management, a setup key for peer enrollment, and a database credential for SQL; these are different privileges. [NetBird Ansible integration](https://docs.netbird.io/selfhosted/iac/ansible)

## Initial Automation Jobs

| Job | Scope | Safety condition |
|---|---|---|
| Inventory and drift audit | Services, networks, published ports, mounts, images and route ownership | Read-only; redact secrets |
| Node baseline | Docker configuration, log rotation, firewall, time sync and inventory labels | Separate bootstrap from app deployment |
| Create or bind database | Pi5 database, role, grants, optional PgBouncer mapping and secret | Existing data is never implicitly reset |
| Publish domain | Public or private DNS, route, certificate and probes | Negative public-access test for private services |
| Deploy application | Build, immutable image, update, health and functional probes | Preserve rollback image and compatible data |
| Enroll external service | NetBird group, resource policy and scoped enrollment | No all-LAN default policy |
| Backup and restore test | Scheduled backups and isolated restore validation | Restores never target production by default |
| Certificate and capacity audit | Expiry, disk growth, container health and resource trends | Notify on actionable changes, not every healthy run |
| Rotate credentials | Versioned secret, consumer rollout and verification | Keep rollback window; never log secret values |
| Retire service | Stop, revoke routes and access, archive configuration | Database deletion is a separately approved job |

The BDS deployment job must preserve its intentional static build: launch a temporary builder attached to a private database-capable network, build the current application without changing its rendering mechanism, produce the runtime artifact, then start the application. Database credentials must not enter image layers, public build output or logs. Keep its Cloudflare connector on `bds-tunnel-net`, never `homelab-net`, and retain application service-name routing.

Start with Ansible Vault or an equivalently encrypted secret source and runtime secret references. Do not add another secret-management service merely to automate the first few applications. Back up Semaphore's encryption material and restrict job-log visibility. Avoid passing arbitrary shell fragments through survey fields.

Cleanup should target explicitly owned resources and retention policies. A global volume prune is not an acceptable scheduled maintenance job. Backup storage, stopped rollback containers and retired application data have different deletion rules.

## Rollout and Acceptance

### Stage 1: Establish Reliable Inputs

Capture live inventory after SSH access is repaired. Reconcile current ports, services and docs. Establish the catalog schema, active Ansible entry point, archived legacy boundaries, secret references and a read-only audit template. Do not mix this work with a full app migration.

### Stage 2: Automate One Existing Service

Deploy Semaphore privately and choose a low-risk existing service as a pilot. Demonstrate idempotent deployment, public/private DNS lifecycle, route validation, rollback, backup metadata and generated documentation. A second unchanged run must make no unintended changes.

### Stage 3: Introduce NetBird

Create the three NetBird databases on Pi5; deploy management on VM100 and relay/STUN on the VPS. Pilot one external peer and one test database. Validate authorized access, denied cross-project access, peer revocation, restart behavior, and loss of relay or control-plane connectivity.

Measure direct and relayed connections separately with representative SQL traffic, reconnects and idle sessions. `NB_FORCE_RELAY` can assist a relay-specific test; it is not evidence that the system automatically selects the lowest-latency path. [Client environment variables](https://docs.netbird.io/client/environment-variables)

### Stage 4: Expand Gradually

Move eligible IP-based container routes to service DNS, add backup/restore and retirement templates, and migrate remaining supported workloads through the same pipeline. Leave money/MyPocket and LLM development outside this change unless separately authorized. Retain human recovery instructions for infrastructure outages.

Before considering the system ready, test recovery in dependency order: Pi5 datastore, Swarm networking, VM100 control services, edge/public ingress, then remote enrollment. Record memory, CPU, disk and concurrent-build peaks before increasing VM resources or assigning hard limits. The documented VM100 allocation is 6 vCPU and 16 GiB; current utilization was not measured successfully.

## Features Not Required Initially

NetBird's public reverse proxy and temporary expose command are relevant future experiments, but the reverse-proxy feature is documented as beta. Keep the established Rathole/Traefik route until a separately approved pilot proves compatibility. Public raw TCP exposure is not a solution for the private database requirement. [NetBird reverse proxy](https://docs.netbird.io/manage/reverse-proxy)

There is also an integration trap: a NetBird migration example suggests a low-priority catch-all TCP router can coexist safely with HTTP routers. Traefik documents that TCP routers are evaluated before HTTP routers. Do not copy a catch-all `HostSNI(*)` onto the existing shared 443 listener. Use narrowly selected SNI names for any pilot and test every existing domain. [NetBird migration example](https://docs.netbird.io/selfhosted/migration/enable-reverse-proxy), [Traefik TCP routing precedence](https://doc.traefik.io/traefik/reference/routing-configuration/tcp/routing/rules-and-priority/)

Community NetBird is sufficient for the proposed private-access pilot. Enterprise capabilities such as active-active management, SCIM and traffic-flow log streaming should not be assumed available in the free deployment. A PostgreSQL backend alone does not grant commercial HA functionality. [Self-hosted enterprise features](https://docs.netbird.io/selfhosted/enterprise)

## Evidence and Documentation Scope

Official references are linked next to their claims. Most documentation is rolling and was accessed on 2026-09-13; the code references are pinned to [NetBird v0.78.1](https://github.com/netbirdio/netbird/releases/tag/v0.78.1). Proposed architecture, workflows, names and safety gates are engineering recommendations, not capabilities claimed to exist in the current lab.

Internal evidence: `docs/MAIN.md`, `docs/PI.md`, `docs/VM100.md`, `docs/INDEX.md`, `edge-registrar/scripts/edge-publish.sh`, `iac/ansible/site.yml`, `migration/edge-stack.yml`, and `migration/traefik/`.

This report adds a proposed decision record only. No service, firewall, DNS, secret, database or deployment configuration was changed. User-facing setup documentation should be written when the pilot establishes tested commands and endpoints; publishing speculative operational instructions now would create further drift.
