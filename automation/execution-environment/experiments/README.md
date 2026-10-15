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

## Static combination follow-up

Upstream `.goreleaser.yaml` sets CGO_ENABLED=0. Repeating the patched build above
with `CGO_ENABLED=0` and output `tofu-homelab-static` produces a native static
ARM64 binary compatible with Alpine, without a glibc compatibility layer.
Use the same pinned builder and source patch; keep the homelab version suffix.
In a disposable context, copy that output as `tofu` and build:

```dockerfile
FROM homelab-automation-ee:alpine-experiment-20261015
COPY tofu /usr/local/bin/tofu
LABEL org.homelab.experimental="true"
```

This combination passes the248 Python test run (247 pass, one skip), native
signed provider readonly init/validate and the unchanged HIGH/CRITICAL scanner
(exit0, zero findings in all four targets). Exact binary/image/report hashes
are in the security record. These local tags and architecture-specific outputs
are experimental inputs, not immutable published release references. Do not
deploy them to the AMD64 runner or infer full upstream test coverage.

## AMD64 emulation evidence

`Containerfile.alpine-static` replaces the local source-image dependency with
the official digest-pinned Docker CLI image and accepts a prebuilt `tofu` in
the disposable context. Supply the same requirements and test-toolchain files
as above. Cross-build the patched source with GOOS=linux, GOARCH=amd64 and
CGO_ENABLED=0 using the pinned native Go builder. Verify ELF architecture and
build metadata before copying the binary into the context. Build explicitly
with `docker build --platform linux/amd64`; do not reuse the ARM64 binary.

The tested AMD64 static binary SHA256 is
`d8f583e3a4e5781d07dc790e2c94315579bbc6486225ff0028fd78286bf44026`.
Local AMD64 emulation passes247 Python tests (one additional opt-in skip),
toolchain, signed provider readonly init/validate, nine Ruby tests, two backup
shell contracts and Ansible lint on62 files. The unchanged scanner exits0 with
zero HIGH/CRITICAL findings. This does not yet prove native VM100 CI execution,
runner integration or reproducible source-to-image supply-chain automation.
The recipe is experimental and does not itself authenticate the supplied binary;
do not promote it as a production build without the remaining provenance gate.
