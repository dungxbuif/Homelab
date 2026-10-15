# Automation image publication security gate

Task 9 of the approved control-plane plan requires image/package security scans.
The existing pipeline validates source and builds images, but publishes them
without a vulnerability gate. This change applies to new automation EE,
Semaphore runner and arm64 provisioner builds, not existing running services.

## Decision and verification plan

Run Trivy 0.76.0 pinned to its observed multi-platform manifest digest before
each push. Export the exact local build to a temporary Docker archive and scan
that archive; do not expose a Docker socket or registry credentials to Trivy.
Block publication on HIGH/CRITICAL findings (including unfixed findings), EOL
OS, scanner/download failures, or missing output. Do not add ignore lists or
allow-failure. Preserve JSON reports for 14 days even on CI failure, but remove
temporary image archives on exit. Reports are private project artifacts.

The scanner needs outbound access to its vulnerability databases. An unavailable
database is a failed gate, not a clean result. Cap scanner CPU/memory; do not
stress production or alter backup schedules. Source-pattern secret scanning
remains separate; this gate does not certify absence of arbitrary secrets.

Tests must prove scanner failure propagates, archive cleanup on success/failure,
pinned scanner/restricted invocation, and scan-before-push for every published
image. Run a real local image scan and inspect the resulting report before
claiming integration works; CI acceptance remains separate from local tests.
Any CVEs found require remediation or an explicit reviewed risk decision, never
silently weakening severity or excluding unfixed findings.

Sources: [Trivy image flags](https://trivy.dev/docs/dev/references/configuration/cli/trivy_image/)
and [release 0.76.0](https://github.com/aquasecurity/trivy/releases/tag/v0.76.0).
Registry manifest observed on 2026-10-15:
`sha256:2416d1f74045b57274df1a340eee6b510cacd73c66a6ccb8da092b117eb7d222`.

Operator docs and machine-readable CI will describe the gate. Public app docs
are unchanged: there is no user API, application behavior or production rollout
in this change.

## Local acceptance and findings

The implementation transfers the archive and report with `docker cp`, not bind
mounts: rootless DinD cannot reliably traverse job-owned 0700 directories.
The scanner runs explicitly as UID/GID 65532 with all capabilities dropped,
no-new-privileges, 1 CPU and 1536 MiB memory. The archive is made readable inside
the disposable container while its containing host directory remains 0700.
Only the exact scanner container ID is removed, including on failure. A cleanup
failure also prevents a successful gate.

Tests: new gate tests failed before implementation, then passed; a separate
archive-read regression failed and passed after fixing its mode. The final
explicit non-root scan reproduced the same findings and retrieved its report.
The automation Python suite passes 75 tests; ShellCheck passes. Review caught
the bind-mount identity problem before publication. API copies were tested
locally, but the actual GitLab rootless DinD job remains the integration gate.

A real scan of local image
`sha256:7c1c46ba421df30d0d8bfdc1c195f8d7e73b559ee2a21f2f478c325a0253792b`
completed with exit 1 and a retrieved JSON report: 194 HIGH plus 12 CRITICAL
package/advisory records (not 206 distinct CVEs). Breakdown: Debian 122, Python
1, Docker CLI 25, OpenTofu 58. The image is NOT cleared for new publication.
This is not evidence that the currently deployed runner has the same findings.
Do not bypass the gate; reconcile dependency versions and scan exact CI builds.

Local report: `/tmp/homelab-image-security.SwmOrT/security-reports/automation-ee-api-nonroot.json`.
SHA-256: `249a0d8da47fbc4224afbfacea1468fbba0134f135d2f9e84364e01ebe029222`.
The report is a local diagnostic, not a durable recovery artifact. No temporary
archive or scanner container remained after the run. No production image,
service, backup process or runner was changed by this local acceptance.

## Dependency remediation candidate

Before editing the toolchain, registry/PyPI/GitHub metadata was checked on
2026-10-15. Candidate versions: Python 3.13.16 on Debian trixie, Docker CLI
29.9.0, OpenTofu 1.13.1, and ansible-core 2.18.19. Keep Ansible on its existing
2.18 minor line; the report identifies 2.18.18rc1 or later as the fix for
CVE-2026-11332. Do not change unrelated Python dependencies or server Docker.
Pin Python and Docker source images by observed multi-platform digest. OpenTofu
retains the release checksum verification during build.

This is a local candidate until build, toolchain checks, policy/Ansible/Tofu
tests and a new vulnerability scan pass. Updating OpenTofu CLI does not import,
refresh or apply any production state. Keep the previous local image tag and
all live runner digests unchanged. New builds must still fail the same security
gate if any HIGH/CRITICAL findings remain; there is no blanket exception.

Sources: [official Python image tags](https://github.com/docker-library/official-images/blob/master/library/python),
[official Docker image tags](https://github.com/docker-library/official-images/blob/master/library/docker),
[OpenTofu 1.13.1](https://github.com/opentofu/opentofu/releases/tag/v1.13.1),
[ansible-core 2.18.19](https://pypi.org/project/ansible-core/2.18.19/).

### Candidate results

Local arm64 build `homelab-automation-ee:security-20261015` completed, image ID
`sha256:76b816a9523e0683255ede05b92bf4bd21737d5b8406bedc92c8e7b1e8ff736b`.
Runtime versions were independently read from the binaries: Python 3.13.16,
Ansible 2.18.19, Docker CLI 29.9.0 and OpenTofu 1.13.1. The original local
image and all production image references remain unchanged.

Verified with this candidate: toolchain smoke, 78 automation tests, 21 Ansible
tests, 70 backup tests, 14 OpenTofu tests (including native encrypted state/plan
fixtures), and Ansible lint on 59 files. Lint had no rule failures; read-only
cache and upstream Python deprecation warnings were emitted. No production
Proxmox state or VM was touched.

The real rescan still exits 1: 85 HIGH and 5 CRITICAL package/advisory records,
38 distinct advisory IDs. Debian has 79 records with no fixed version reported;
the Docker CLI has none; OpenTofu's official release has 7 Go dependency/runtime
records. Four Python records are from pip's vendored msgpack/setuptools/urllib3,
not the separately installed urllib3 2.8.0. `pip._vendor/vendor.txt` confirms
those old versions even though pip 26.2.1 is the latest published release at
this observation. Do not falsely claim upgrading the top-level urllib3 fixes
pip's bundled copy, or claim that no reported fix means a vulnerability is safe.

Local candidate report:
`/tmp/homelab-image-security.SwmOrT/security-reports/automation-ee-patched.json`.
SHA-256 `66e8efb13fc1063a505ec098aaf7f94ed74fd5b8b4a99ec3b8a6cf7a2439137a`.
The candidate is still blocked for publication by the unchanged gate; remediation
or individually reviewed, scoped risk decisions remain open. CI amd64 and real
rootless DinD scanning are separate pending acceptance gates.

Prior pipeline 69/job 165 failed before reaching the scanner during Galaxy
installation (`KeyError: results`, old ansible-core 2.18.6). The candidate's
Galaxy install succeeded locally, but this does not prove the CI failure cannot
recur. No running job was canceled or restarted to work around that failure.

## Actual rootless CI acceptance and provisioner remediation

Pipeline 70 passed both validation jobs. Jobs 170 (EE) and 171 (provisioner)
then completed actual Trivy scans through rootless DinD, retrieved JSON reports,
uploaded private artifacts, and stopped before push with exit 1. The amd64 EE
report matches the local candidate's 90 findings. Runner build/scan was not
reached because EE publication was blocked, so it is not certified.

The arm64 provisioner report has zero Alpine OS findings, four pip-vendored
Python records and 25 records in Docker CLI 27.5.1 (including one CRITICAL).
Next scoped remediation: use the already verified Docker CLI 29.9.0 digest,
and remove pip from the final provisioner runtime using its native uninstall.
The service has no dependency-install step or runtime use of pip: it runs the
standard-library HTTP server and copied provisioning modules. Do not remove
Python, Docker CLI or any provisioning module, or apply this removal to the
general EE without separate compatibility evidence.

Verify candidate import/startup contracts and absence of pip, rescan the exact
image with the unchanged gate, and keep live provisioner untouched until an
approved digest deployment with its own acceptance. This does not authorize
rotating database credentials or reprovisioning any database.

The arm64 provisioner candidate built successfully as
`sha256:b7836fa656b675f69d05c892b81d2febb4898f842943de3636e62d13d194bdc5`.
Native image checks confirmed no importable pip, Docker CLI 29.9.0, server
health 200 and unauthenticated provision rejection 401 in a network=none,
256-MiB/1-CPU disposable container with no Docker socket or production data.
All 17 provisioner Python tests and four toolchain-source tests passed.
Review found no runtime dependency omitted by removing pip. Compatibility with
the target Docker daemon remains a separate live read-only acceptance check.

The unchanged Trivy scan returned exit 0 with zero HIGH/CRITICAL findings in
the Alpine OS and Docker binary; no Python package findings remained. This is
not a claim of absolute security. Local report
`/tmp/homelab-image-security.SwmOrT/security-reports/provisioner-patched.json`,
SHA-256 `7b6eae040106cfda0c5be2c0376a7f001e1d82cd007197c4382dec11c8a98851`.
Actual new CI build/publication and production rollout are not yet completed.

## Pipeline 71 follow-up

Pipeline 71 at published commit `50ca1663` passed validation jobs 172 and 173.
EE build job 174 failed; provisioner job 175 failed before reaching its scanner.
The provisioner's amd64 import smoke passed, but the arm64 build failed executing
`python -m pip uninstall --yes pip` with `/bin/sh: exec format error`.
The new native RUN instruction requires an arm64 builder or explicitly managed
emulation; local arm64 build success did not establish amd64 CI cross-build
support. No new provisioner image was published or deployed by this job.

Before changing the build, select and document a controlled native-arm64 or
cross-build implementation, then verify both target architectures and repeat
the unchanged pre-push scan. Do not install privileged host binfmt handlers as
an implicit workaround or bypass the vulnerability gate. Public app docs are
unchanged because this concerns only internal image delivery.

### Cross-build repair decision

Use the same pinned Python image twice: a target-platform filesystem source and
a BUILDPLATFORM preparation stage. Copy the target root filesystem under
`/target`, remove only pip's package, distribution metadata and console scripts
using the native builder's Python, and copy that filesystem into a scratch final
stage. The final image retains Alpine, target Python, CA certificates and all
system libraries; scratch is only the assembly stage, not a replacement runtime.
Restore the observed runtime PATH and existing provisioner entrypoint explicitly.
Upstream Python build-only GPG/version/hash environment metadata is not required
by the service; immutable source digests remain the provenance reference.

Test removal against a disposable filesystem, require the expected pip layout
before mutation, preserve unrelated packages, and reject symlinked inputs. Build
both architectures, run native runtime smoke and the unchanged vulnerability
scan, then confirm the amd64 CI runner can produce arm64 without emulation.
No production rollout is included until these gates and target-daemon acceptance
pass. This supersedes target-native pip uninstall, which failed in pipeline 71.

Local verification: 82 automation tests and 17 provisioner tests passed. Both
architectures built successfully using the native preparation stage. ARM64 image
`sha256:db64c1c9e05117970c016f81769fb3f090a067d667b6331bc3eb9858e5ce0f79`
passed native Python/server import, pip-absence and Docker CLI checks with no
network, socket or production data. AMD64 assembly produced
`sha256:9ee3ed75bbdb054766f631df1a2bb1912c1095a1a0bb467ee9b839108d117175`;
this build alone does not certify native amd64 execution.

The ARM64 rescan exited 0 with zero HIGH/CRITICAL records, report SHA-256
`b0cb3b2af88b55f136451b8ed6aac62573d3d0f601ea4dab261d9b3617a2ed02`.
Independent scoped code review found no blocker. Actual amd64 runner acceptance
and target-daemon compatibility remain pending; production is unchanged.

## CI-verified provisioner rollout gate

Pipeline 72 validators passed; job 179 completed native amd64 smoke, amd64-to-
arm64 cross-build, the unchanged vulnerability scan and image publication.
The scan has zero HIGH/CRITICAL records; artifact SHA-256 is
`43e3982eaa95d2f50abb6f11fcbc26f564f6539d565cff2929d271d734642f3d`.
Published image:
`registry-gitlab.dungxbuif.com/dungxbuif/homelab-automation/provisioner@sha256:c7b60154e9d445bc0cb445fecf6ecae92f0de107ec672c14c77750515ebb59d3`.
The EE job remains failed and is not covered by provisioner acceptance.

Proceed through `provisioner-release.yml` under the approved control-plane
implementation scope, after rechecking Semaphore has no active provisioning
tasks. Preserve the previous service spec and temporary-registry-auth cleanup.
Post-check actual Docker client/server negotiation plus health, baked imports,
pip absence and the existing 401/409/422 native lock probe. Do not create an
application database or restart backup jobs. Record actual receipt/outcome below;
publication alone is not deployment evidence.

### Live Pi5 result

Release completed through Ansible: 17 tasks OK, 7 changed, zero failed or
unreachable. Previous spec and sanitized receipt are preserved at
`/ssd-data/infra/provisioner/releases/provisioner-release-j31r8olp`.
Temporary registry credentials were removed by the playbook. Container
`6d395b007b04` reports the exact CI-published `c7b60154...ebb59d3` image above.
Baked imports and private HTTP health passed.

The existing opt-in lock probe passed on this live container: unauthenticated
401, locked 409, unlocked unsupported engine 422, native DB mutations false.
Actual client/server negotiation returned Docker CLI 29.9.0 and daemon 28.4.0;
pip is absent. No application database or backup job was modified or restarted.
This release reuses unchanged provisioning logic; fresh create/replay/cleanup
was not repeated for this security-only image. Earlier native acceptance is
recorded separately, not relabelled as a test of this new digest.

## EE build-tool removal candidate

Pipeline 78/job 194 still reports 90 HIGH/CRITICAL records, including four in
pip's bundled dependencies. Installed dependency metadata has no mandatory
runtime pip dependency among these tools; ansible-lint lists pip only for its
optional test extra. Ansible-compat source has no runtime pip invocation.
This is a reason to test removal, not compatibility proof.

Remove pip with its native uninstall AFTER Python and Galaxy dependency
installation. Dependencies must be baked at build time; runtime pip installation
is not supported by this candidate. Build a new local tag, preserve old images
and live runner digests, verify pip absence, run toolchain/Ansible lint and all
automation/backup/OpenTofu tests, then rescan with the unchanged gate. Any
compatibility failure blocks adoption. Remaining OS/Go findings still block
publication; no risk exception or full security clearance is implied.

Candidate result: `homelab-automation-ee:no-pip-20261015`, image ID
`sha256:6509000682bce4bdb8ff98fe771f19014dfd472c8ff2abac95294b79e289606b`.
Toolchain smoke (including pip absence) passed; 95 automation, 21 Ansible,
98 backup (one opt-in skip), and 15 OpenTofu tests passed with that image.
Ansible lint passed on 61 files, with existing read-only-cache/deprecation
messages but no rule failures. This is local arm64 compatibility evidence;
actual CI amd64 and derived runner acceptance remain separate.

The unchanged rescan still exits 1: 81 HIGH plus 5 CRITICAL records, now 86
instead of 90. Python and Docker CLI report zero; Debian still has 79 records
and OpenTofu seven. No ignore file or severity filter was relaxed. Report:
`/tmp/homelab-image-security.SwmOrT/security-reports/automation-ee-no-pip.json`,
SHA256 `40d5207ebc74337f6ce87ea675a6ed3b360aa62f4f3a72197913622332d3670b`.
Do not deploy this candidate or claim the EE security gate is clear.
