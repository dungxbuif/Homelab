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
