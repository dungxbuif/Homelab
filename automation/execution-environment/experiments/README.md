# OpenTofu dependency remediation experiment

Not a production image recipe or authorization to replace the executor.
The main Containerfile still consumes the official OpenTofu release.

`opentofu-1.13.1-dependencies.patch` is generated from upstream commit
`233700b795b6d2372f1c56ed57a4abaec9d36475` (tagv1.13.1). It changes only
go.mod/go.sum, using native Go resolution for x/net0.60.0, its required
x/mod0.41.0 and grpc1.83.2. Required transitive Go modules also move; no
application source, provider protocol or state-encryption code is patched.

Reproduce in a disposable checkout, never the production workspace:

```sh
git apply --check /path/to/opentofu-1.13.1-dependencies.patch
git apply /path/to/opentofu-1.13.1-dependencies.patch
```

Use official `golang:1.27.2-bookworm` pinned to index digest
`sha256:5cf287a799e6b94384bad13d16b14904c531f51ba65792237e122ce42b392f61`.
Keep checksum verification enabled and GOTOOLCHAIN=local. Build with:

```sh
go build -p=2 -mod=readonly -trimpath -buildvcs=true \
  -ldflags '-X github.com/opentofu/opentofu/version.dev=no -X github.com/opentofu/opentofu/version.rawVersion=1.13.1-homelab.1' \
  -o tofu-homelab ./cmd/tofu
```

The modified version must remain distinguishable from official1.13.1. Preserve
the source revision, patch and builder digest with the binary. Do not disable
module checksums, remove vulnerabilities from scan output or alter module
metadata to manufacture a clean result.

Local ARM64 evidence: actual version1.13.1-homelab.1, Go1.27.2 build metadata,
encrypted-state tests, readonly provider init/validate, and248 suite tests
(247 passed, one opt-in skip). Unchanged Trivy gate finds zero HIGH/CRITICAL in
the patched OpenTofu binary, but79 in Debian, so the combined image still fails.
AMD64 rebuild, broader upstream tests, base remediation and CI/runner adoption
remain unverified. See the [security record](../../../docs/deployments/automation-image-security-2026-10-15.md).

## Alpine compatibility candidate

`Containerfile.alpine` is an experimental recipe, not used by CI or production.
Prepare a disposable build context containing this file as Dockerfile, the
parent requirements.txt and requirements.yml, and
`automation/execution-environment/tests/test-toolchain.sh` as test-toolchain.sh.
It requires the local
`homelab-automation-ee:no-pip-20261015` image (recorded source image ID
`6509000682bce4bdb8ff98fe771f19014dfd472c8ff2abac95294b79e289606b`)
for the original Docker and OpenTofu binaries. Do not pull a similarly named
third-party image. This local dependency is not a portable release recipe.

Alpine packages resolve from the pinned base's repositories, not a frozen
package snapshot. Rebuilds therefore require fresh compatibility tests and
security scans. Ruby includes JSON; use the dedicated flock package because
BusyBox flock does not implement the required contention exit-code option.

Native ARM64 suites pass (247 tests, one opt-in skip). The scanner still fails
on seven original OpenTofu HIGH findings, with zero HIGH/CRITICAL in Alpine,
Python and Docker CLI. The glibc-linked patched binary above is NOT compatible
with this musl base. Static/musl remediation, AMD64 execution, full CI and runner
integration remain required; this is not an approved executor replacement.
