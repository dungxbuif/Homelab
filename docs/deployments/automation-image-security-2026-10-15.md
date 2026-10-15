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
