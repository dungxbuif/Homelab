# Application catalog reconciliation

The deployment catalog still mixes proposed limits with observed settings and
uses `deployable` to mean digest-shaped rather than an enrolled release path.
Before more application rollouts, correct this metadata against the restricted
observer evidence and selected Docker inspection. No app changes in this step.

Observed on VM100:

- KubeKosh: Compose, privileged, `homelab-net`, 2 CPU / 4 GiB memory and 1 GiB
  reservation, persistent bind `/opt/apps/kubekosh/data` -> `/data`. Its
  previously declared network `lan-only` is a Traefik middleware, not its Docker
  network. A Swarm migration must address privileged execution and persistence;
  do not substitute an untested service with reduced privileges.
- GitLab: Swarm, 4 CPU / 10 GiB (not Compose / 8 GiB).
- Stirling: Swarm, 2 CPU / 2 GiB (not 1 CPU).
- Homepage, RelayHub API, OCR proxy, MyPocket API, OpenClaw, n8n and BDS app have
  no explicit container CPU/memory hard limit. Record `{}` rather than invented
  runtime limits; retain earlier proposals separately, not as applied policy.
- BDS app is attached to both `bds-tunnel-net` and `homelab-net`.
- OCR proxy uses `edge-http-net` plus `homelab-net`; n8n uses `data-net` plus
  `edge-http-net`; MyPocket API uses `data-net`, `homelab-net`, `mypocket-net`
  and `mypocket-redis-net`. These are observed boundaries, not proof the wider
  networks are necessary. Its observed API tag is `auth-12572c87`; the worker
  still uses `release-73c4c37`. Do not upgrade the worker implicitly.
- RelayHub `/readyz` and MyPocket `/api/v1/health` return HTTPS 200 through both
  Pi and VPS; their catalog `/health` paths were stale.

Selected `docker image inspect` confirms local RepoDigests for KubeKosh,
Stirling and OCR match their recorded hashes. This does not prove a new node
can pull the OCR `homelab/...` repository or that a release job exists.

Contract change: `deployable: true` requires an explicitly enrolled release
template as well as the current metadata checks; truthy strings are invalid.
Only Homepage has that boundary currently (template 6). Keep other services
listed but not automation-deployable until their real apply/verify/rollback
path is enrolled. This does not disable or stop their running containers.
The verifier is preflight only, not approval authorization or proof of runtime
health. Actual release authorization remains in the forced-command helper.

Verification: regress missing release boundary and non-boolean readiness;
assert corrected health paths, runtime mode/networks/resources, and keep the
Homepage exact approved digest acceptance passing. Run the automation suite
and review before publication. Update the operator catalog README; public app
docs need no changes because application behavior is unchanged.

## Result

Corrected catalog fields and preflight are implemented. All 68 automation
Python tests pass, including the newly reproduced missing-template/truthy-flag
failures and runtime metadata checks. Focused review found no blockers. Existing
Homepage release remains accepted; three unenrolled applications now fail
preflight instead of appearing automation-ready. No containers were stopped,
updated, or removed and no resource limits were applied.

VPS SSH with the configured agent failed signing and then exceeded server key
attempts; an explicit local key also returned permission denied. Therefore
Stirling's public gateway fix remains pending, not completed. Its earlier
deployment note records a missing VPS HostSNI entry; current certificate failure
is consistent with that but live gateway configuration still needs inspection.
Retention remains active under PID 1133089; at 01:41:05 UTC it was checking
snapshots/trees/blobs. No second retention process was started.
