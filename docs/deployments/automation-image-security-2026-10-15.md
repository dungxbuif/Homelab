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
