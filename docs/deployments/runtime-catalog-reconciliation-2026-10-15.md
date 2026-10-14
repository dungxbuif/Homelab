# Runtime catalog reconciliation

Read-only Docker container/image/network observations on Pi5 and VM100 at
2026-10-15 show that the initial active policy still describes old networks.
Correct the policy before it becomes input for deployment automation. This
change must not attach/detach any running container or change public routes.
Mark the catalog incomplete, and distinguish verified restricted host audit
from unimplemented general apply access. Do not claim VPS enrollment exists.

Observed corrections: Semaphore is only on homelab-control-net; its runner is
on VM100 on that same network; provisioner is on control plus homelab-net.
Homepage is on edge-http-net. CouchLoom uses couchloom-internal (app also on
homelab-net), BDS app uses bds-tunnel-net plus homelab-net, and its Cloudflare
connector only bds-tunnel-net. KubeKosh actually uses homelab-net; LAN-only is
an exposure policy, not a Docker network name. Pi edge, datastore and registry
networks also need to match the observed Docker network names.

Verify policy parser, regression tests and declarative audit output; successful
validation must remain not_verified, not a statement of live service health.
Public app docs do not change because no public behavior changes.

VPS SSH preflight through alias gateway failed with agent signing communication
failure followed by too many authentication failures. The agent lists multiple
keys. Retry with only its existing Gateway public identity (private key remains
in 1Password), strict host trust, and IdentitiesOnly. This is diagnostic bootstrap
access, not production observer enrollment. Never change sshd or authentication
policy to bypass agent approval.

## Reconciled result

The policy now reflects the observed network corrections and includes the
previously missing Semaphore executor and BDS connector. `inventory_complete`
is explicitly false. Pi/VM100 list only their verified restricted capabilities;
VPS bootstrap and OpenTofu import remain pending instead of being presented as
deployed transports. No live network was changed.

Regression tests failed against the old Semaphore network, then passed after
the update in the pinned local execution image (4 tests). Policy validation
reports 5 hosts, 24 logical services, 8 routes, 3 backup classes and zero
Kubernetes infrastructure targets. The 5 inventory contract tests also pass
with 75 assertions. The first host-side test attempt additionally hit missing
PyYAML in its child interpreter; the execution-image run is the valid test.

This remains a partial catalog: additional VM100 apps and Pi monitoring/data
components observed during the audit still require individual ownership,
component and route reconciliation. Do not delete omitted resources or use
this file as a complete replacement deployment manifest.
