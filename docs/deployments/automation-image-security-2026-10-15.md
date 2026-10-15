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

## Actual AMD64 CI scan

Pipeline86/job222 failed the unchanged image gate after validation221 passed.
Artifact `security-reports/automation-ee.json` SHA256:
`57ebd95be3d3698f83aed7fe462668b888c24689ae64df00deed7d7edf2ca982`.
It independently confirms86 findings: Debian74 HIGH+5 CRITICAL, OpenTofu7 HIGH,
Python0 and Docker CLI0. No Debian finding in this artifact advertises a fixed
version; that is scanner metadata, not a claim that no upstream mitigation exists.

OpenTofu1.13.1 embeds vulnerable Go1.27.1 and dependencies. Scanner-reported
fixed versions include Go1.27.2, x/mod0.40.0, x/net0.60.0 and grpc1.83.2.
An official patched release or separately reviewed reproducible rebuild is
required; changing version strings or suppressing findings is not remediation.
The runtime EE remains unapproved. Derived runner publication/adoption must not
proceed from this failed image. Provisioner uses its separate image/gate and
must not be conflated with this EE result.

## Isolated OpenTofu remediation experiment

Prepare an isolated source build from upstream tagv1.13.1, observed peeled
commit233700b795b6d2372f1c56ed57a4abaec9d36475. Test Go1.27.2 and the minimum
scanner-reported fixed module versions (x/mod0.40.0, x/net0.60.0, grpc1.83.2).
Keep native Go checksum verification enabled and inspect the resulting module
diff; no automatic upgrade of unrelated dependencies. Preserve upstream source
and distinguish any modified build from the official release in its provenance.

This is a local candidate experiment only: no replacement of the production EE,
runner or existing local known-good tag. Verify build metadata, native encrypted
state tests and provider init/validate, then rescan without exclusions. A clean
Go scan alone cannot clear the separate Debian findings. Record incompatibility
or unavailable toolchain honestly; do not rename versions to bypass the scanner.

Native dependency resolution rejected x/mod0.40.0 because x/net0.60.0 requires
x/mod0.41.0; the failed attempt left source unchanged. Use the explicit required
0.41.0 floor for the experiment, not `latest`. Builder image is the official
Go1.27.2 Bookworm index pinned at
`sha256:5cf287a799e6b94384bad13d16b14904c531f51ba65792237e122ce42b392f61`.
Local containers are limited to2CPU/4GiB/512PIDs and mount only the disposable
source checkout, not homelab credentials or Docker sockets.

### Experiment outcome

Native ARM64 build succeeded as `OpenTofu v1.13.1-homelab.1`, with Go1.27.2
metadata and the pinned upstream revision marked modified. Source diff contains
only9 module version changes and18 new checksum entries. The generated patch
and reproduction notes are retained under execution-environment/experiments;
the main Containerfile is unchanged.

Candidate image `homelab-automation-ee:tofu-patched-experiment-20261015` has ID
`sha256:7298483e75c1f832cb36eddaf33a770119d2e6b811e2ce09081ce9280711af95`.
Binary SHA256: `e503994fb350293e0748aec8f885f1979079950642f72843097cd006955bf9c8`.
The native encrypted-state test and readonly Proxmox provider init/validate pass.
Full suites: automation111, Ansible24, backup98 (one opt-in skip), OpenTofu15;
247 tests pass, one skips. No live Proxmox API/state was used.

Unchanged Trivy scan exits1 because Debian retains74 HIGH+5 CRITICAL. OpenTofu,
Docker CLI and Python now each report zero HIGH/CRITICAL. Full report SHA256:
`939ebd99ce657cbc81baf37d26941551effaff04469e5945f33431841ee5ab9a`, stored at
`/tmp/homelab-tofu-remediation.fIFciK53/security-reports/automation-ee-tofu-patched.json`.
This experimentally resolves the seven Go findings, not the complete EE gate.
No image was published or adopted by a live runner. AMD64 candidate compatibility
and broader upstream test coverage remain open before any adoption decision.

## Base-distribution compatibility experiment

The remaining79 records span util-linux, Ruby, OpenSSH, curl, Expat and other
system libraries; deleting scanner metadata or stripping essential packages
would not be a valid fix. Test a separate Alpine3.24 Python3.13.16 candidate,
official index pinned to
`sha256:2d9aefe2fef018a7eb2c13064c89c71929800fd2e5dccdbf52ea5da5bb8d929a`.
Keep Python/Ansible collection versions unchanged, install native equivalents
for shell/Ruby/GNU utilities, run compatibility tests and the unchanged scanner.
Record actual package versions after resolution. Do not change production or
the main Containerfile on the strength of a base-only scan.

The patched OpenTofu experiment is glibc-linked, so it cannot simply be copied
into musl Alpine. First isolate base/tool compatibility using the existing
official binary where compatible; then build a separately verified static or
musl candidate if the base proves useful. Do not add a hidden glibc shim merely
to make smoke tests pass. No automatic adoption is authorized by this experiment.

First native ARM64 Alpine build passed toolchain smoke. Its unchanged scanner
reported zero HIGH/CRITICAL for Alpine, Python and Docker CLI, but seven HIGH
findings in the original OpenTofu binary; the overall security gate still fails.
Compatibility suites initially found three backup enrollment failures because
BusyBox flock lacks `-E` (custom lock-contention exit code). Install Alpine's
dedicated `flock` package, confirmed available as 2.42.3-r1, and rerun the same
tests and scan. Do not weaken the lock contract or alter production scripts.
Ruby 3.4.9 includes JSON; separate `ruby-json` does not exist in this repository.

After adding flock, all four suites pass: automation111, Ansible24, backup98
(one opt-in skip), OpenTofu15: 247 passed, one skipped. Candidate image ID is
`sha256:3a63f9b646a084dc546ba22125e413b98f6039d8781d93b61c1c67b7c042180c`.
Rescan still exits1: zero HIGH/CRITICAL in Alpine3.24.2 (67 packages), Python
and Docker CLI; seven HIGH in original OpenTofu. Report SHA256:
`c9ae1df2982030933d376919ad45d5dd9d254068a8af099d020238e8e1093b1b`.
Report: `/tmp/homelab-alpine-ee.UXMiFFL8/security-reports/automation-ee-alpine-flock.json`.
Recipe preserved under experiments/Containerfile.alpine, with local-only source
image dependency documented. No runtime image, CI recipe or production service
changed. These tests do not prove AMD64, runner integration or full upstream
OpenTofu behavior. Public application docs are unaffected by this internal trial.

## Static OpenTofu follow-up

Upstream v1.13.1 `.goreleaser.yaml` explicitly builds with `CGO_ENABLED=0`.
Rebuild the existing dependency-patched disposable checkout with that setting,
the same pinned Go1.27.2 builder and distinguishable homelab version. Preserve
the earlier glibc binary, write a separate static output, and verify its ELF
linkage/build metadata before combining it with the Alpine candidate. Require
toolchain, encrypted-state, signed provider init/validate and unchanged security
scan evidence. This remains a local experiment, not runner replacement approval.

Static ARM64 build completed successfully. `file` confirms a statically linked
ELF; Go metadata confirms Go1.27.2, CGO_ENABLED=0, upstream revision
233700b795b6d2372f1c56ed57a4abaec9d36475 and vcs.modified=true. Binary SHA256:
`581fb3f55f7351a13e32d72ba211b27f79658e8f1d68de915da22730ead32884`.
The original glibc output was not overwritten.

Combined local image `homelab-automation-ee:alpine-static-experiment-20261015`
has ID `sha256:9e85076e9e5d34fa5f68f321b7ccf8360d1bd5e4773fee998f56edfbca118a02`.
Toolchain smoke passes. All248 Python tests run:247 pass and one opt-in skip,
including actual state/plan encryption with correct, wrong and missing keys.
Readonly provider init installs signed bpg/proxmox0.116.0, key0B3405B36193A495;
actual module validate passes without live Proxmox credentials or state.

Unchanged Trivy scan exits0: zero HIGH/CRITICAL in Alpine, Python, Docker CLI
and OpenTofu. Report SHA256:
`8ddc28d6ac0c94dcc3a1b5139b102b19cf513ad958bb8331855a608b1d6fbb16`.
Report path: `/tmp/homelab-alpine-static.fHkNv7el/security-reports/automation-ee-alpine-static.json`.
No ignore rules, severity downgrade, metadata stripping or scanner change was
used. This is point-in-time ARM64 candidate evidence, not a guarantee of absence
of all vulnerabilities. The base Alpine candidate also passed full Ansible lint
(62 files), ShellCheck error gate, nine Ruby tests and upload/Restic shell tests.
AMD64 build, broader upstream tests, portable CI recipe, runner integration and
operator adoption remain outstanding. Production has not changed.

## AMD64 candidate validation plan

Cross-build the same patched source with the pinned native Go builder,
CGO_ENABLED=0, GOOS=linux and GOARCH=amd64 into a separate output. Inspect
ELF/build metadata, then construct a separate AMD64 Alpine image using the
official pinned multi-platform Docker CLI image rather than copying the ARM64
binary. Run toolchain, encryption/provider and compatibility tests and the same
scanner under local AMD64 emulation. Emulation evidence is not native VM100
runner acceptance; no deployment or CI runner replacement is included here.

Cross-build completed: ELF x86-64, statically linked; Go metadata confirms
Go1.27.2, CGO_ENABLED=0, GOARCH=amd64, exact upstream revision and modified=true.
Binary SHA256: `d8f583e3a4e5781d07dc790e2c94315579bbc6486225ff0028fd78286bf44026`.
Candidate `homelab-automation-ee:alpine-static-amd64-experiment-20261015` image ID:
`sha256:d051a656cc464b973de652023bd39da883a3cadb2197eb25eb10ec3490995040`.

Under local AMD64 emulation: toolchain passes, Python suites run248 tests with
247 passes/one skip, including the native CLI encryption test. Actual provider
init uses readonly lock and signed bpg/proxmox0.116.0; module validate succeeds.
Base image passes nine Ruby tests, upload manifest and Restic shell contracts,
and Ansible lint on62 files. No production credentials or Proxmox state used.

Unchanged Trivy scanner exits0; all four targets have zero HIGH/CRITICAL.
Report SHA256: `e908db68237f8d14d0ff3cba3613692dc60279046887d4d8520da321743f51c9`.
Report: `/tmp/homelab-alpine-amd64.IQ0ggfSp/security-reports/automation-ee-alpine-static-amd64.json`.
Recipe retained as experiments/Containerfile.alpine-static. No main CI recipe
or production runner changed. Native CI, complete runner boundary checks,
broader upstream tests and provenance-enforcing build remain acceptance gates.

## Native VM100 candidate check

The AMD64 candidate was pushed only under the immutable experimental registry
tag `alpine-static-amd64-experiment-20261015`, digest
`sha256:835cce544bde8fba8a381929d2e59dd8a95019c83c83f7ebb84e090cdd76c0a6`.
VM100 could not pull it through its rootful daemon because that daemon has no
registry credential; no credential was copied to the host. For the controlled
read-only check, the exact image archive was transferred to a mode-0600 `/tmp`
file, loaded, and tagged locally. The archive, local image, and all temporary
module/test directories were removed after verification; the registry artifact
remains for traceability.

On native VM100, toolchain smoke passed, and OpenTofu initialized the Proxmox
module with signed `bpg/proxmox` 0.116.0 (key `0B3405B36193A495`) and validated
the configuration. The one-test encryption suite passed with correct, wrong and
missing passphrases. No live Proxmox API, state backend, Docker socket or
production mount was used. This closes candidate host-architecture evidence,
not the production adoption gate: registry pull credentials, native CI job,
runner digest enrollment, full job boundary acceptance and reproducible
source-to-image build are still required.

The explicit native gate then passed as GitLab pipeline99, job235, using the
VM100 project runner and candidate digest
`835cce544bde8fba8a381929d2e59dd8a95019c83c83f7ebb84e090cdd76c0a6`.
Evidence from the job: toolchain smoke; ShellCheck; Ansible lint with zero
failures on62 files; Python suites 111,24,2,97 and15 tests (97 includes one
opt-in skip); Ruby inventory/template contracts; backup upload/Restic contracts;
signed bpg/proxmox0.116.0 init/validate; and tracked-file secret scan. The
runner pulled the private digest with GitLab job credentials, used rootless
Docker27.5.1 DinD over TLS, and reported x86_64/6 CPU/15.61 GiB in the isolated
job daemon. No production mounts or Proxmox apply were used. This closes native
candidate execution evidence, but not promotion of the experimental image to
the default executor or the remaining full end-to-end control-plane gates.

Pipeline97 then reached the native suite but `ansible-lint` could not resolve
role `base` because the candidate job did not set `ANSIBLE_CONFIG`; local
validation had supplied it explicitly. Set the job variable to the checkout's
absolute `automation/ansible/ansible.cfg` path and rerun. This is a test-runner
configuration correction, not a role or production change.

Experimental pipeline95 pulled the exact digest on VM100 and reached the job
container. Its first script failed because the custom image does not inherit
the Docker CLI image entrypoint that exports TLS client variables for the
rootless DinD service. Declare `DOCKER_CERT_PATH` and `DOCKER_TLS_VERIFY` in the
experimental job; keep TLS enabled and do not fall back to plaintext port2375.

The runner allow-list now admits this exact experimental digest alongside the
existing Docker CLI images; it does not admit a wildcard. The Ansible runner
install playbook restarts only the project runner when its rendered config
changes, so the allow-list cannot remain stale in the running process.

## Production recipe adoption checkpoint

The current Debian-based main recipe is still rejected by the unchanged scan:
the latest report contains 5 CRITICAL and 74 HIGH findings. A disposable
Alpine/static OpenTofu candidate has already passed the same scan with zero
HIGH/CRITICAL findings and passed the native VM100 candidate gate, but its
OpenTofu binary was supplied from a separately prepared local artifact. That
is evidence for the base choice, not a reproducible production build.

The main recipe now makes that candidate reproducible: it compiles the patched
OpenTofu source from the pinned upstream commit with the pinned Go builder,
verifies the patch and module checksums, then copies the static binary into the
digest-pinned Alpine image. The local ARM64 build produced
`OpenTofu v1.13.1-homelab.1`; ShellCheck, Ansible lint on 62 files, and the
full local suites passed (115 automation, 25 Ansible, 2 Semaphore, 98 backup
with one opt-in skip, and 15 OpenTofu tests). The unchanged scanner exited 0
with zero HIGH/CRITICAL findings; report SHA256 is
`0a16321673649abea3aaa714c7a41363e6938d6aed507ffda1a0b8f0af166a77`.

This is still a local pre-publish result. The normal GitLab pipeline must build
the same source-to-image recipe, scan both executor images, and pass the
native runner boundary before the new digest is enrolled. Until then the
existing executor remains unchanged.

The first local runner build exposed a separate blocker: copying Semaphore
`v2.19.12` into the otherwise clean Alpine runner added 9 HIGH Go findings
(Docker Engine, go-git, x/crypto, x/net, x/text and Go stdlib). The runner
recipe was tested with the pinned latest stable Semaphore `v2.19.16` digest,
but it still reports the same 9 HIGH findings. It is rejected. The server
deployment is not changed by this executor-image experiment. Test the newer
`v2.20.0-alpha4` binary only as an isolated compatibility candidate; it must
clear the strict runner scan and pass runner smoke before it can be considered.

The isolated alpha candidate passes runner smoke, but its unchanged scan still
reports 3 HIGH findings: two `github.com/docker/docker v28.5.2` records with
no scanner-advertised fixed version and `golang.org/x/net v0.58.0` fixed at
`0.60.0`. It is also rejected for production. The remaining Docker findings
belong to the proprietary Semaphore runner binary, not the Docker CLI copied
into the image, so changing the Alpine base cannot remove them. The next valid
remediation requires a vendor-patched Semaphore runner build or a reviewed
executor design change; no scanner suppression or metadata stripping is
acceptable.

## Explicit native runner gate

Add a CI-only experimental job selected by `EXPERIMENTAL_EE_ONLY=true`. It uses
the immutable candidate digest, the existing project rootless DinD service, and
the VM100 project runner. All normal validation/build jobs are skipped in this
mode. The job must run toolchain smoke, the repository Python suites, Ansible
lint, ShellCheck and Proxmox module validation; it must not apply infrastructure,
mount production data or enroll the candidate as the default executor. Trigger
the pipeline explicitly after publication and record its job/pipeline result.

## Pipeline 117 separation decision

Pipeline 117 at commit `f6fa1f861d793420e6df5be7463b990cdd5eca22` reached the
intended evidence point: validation jobs passed, the provisioner build and
unchanged Trivy gate passed, and the published arm64 image was
`registry-gitlab.dungxbuif.com/dungxbuif/homelab-automation/provisioner@sha256:010cb5a13d0c1240b56c933c7f202c4179d030724b35134c5da3b9d0ef3e05c1`.

The automation EE was also published after its scan. The combined job still
failed because the Semaphore runner candidate contains three HIGH findings in
the vendor binary (`github.com/docker/docker` CVE-2026-41567 and
CVE-2026-42306 with no fixed version reported, plus `golang.org/x/net`
CVE-2026-78669). This is a candidate failure, not a production rollout.

The CI contract now keeps `build:automation-ee` focused on the production EE
image and moves the Semaphore runner candidate to
`build:semaphore-runner-candidate`. That job is created only when the explicit
`BUILD_SEMAPHORE_RUNNER_CANDIDATE=true` variable is supplied; when run, it
retains the same scan-before-push gate and fails on the same policy. This lets
the safe EE/provisioner release path complete without publishing or enrolling
the unremediated runner. No active Semaphore runner or production service was
changed by this separation.
