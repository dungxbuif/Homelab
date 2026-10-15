# Homelab automation execution environment

This is the single pinned toolchain for infrastructure jobs. Semaphore and
GitLab CI should use the image built from `Containerfile` with the immutable
`$CI_COMMIT_SHA` tag and the digest returned after push. A mutable tag is not a
production executor reference.

The image contains:

- pinned `ansible-core`, `ansible-lint`, `yamllint`, and required collections;
- OpenTofu from a pinned release with checksum verification and Docker CLI
  from a digest-pinned source image;
- ShellCheck, Ruby, `jq`, and SSH client for policy and route validation.

Python and Galaxy dependencies are installed when building the image. The EE
candidate removes pip afterward to avoid shipping its vulnerable bundled
libraries. Jobs requiring additional Python packages must update the reviewed
requirements and rebuild the image, not install packages at runtime. This
candidate has not replaced the live Semaphore runner and still requires the
unchanged security and compatibility gates.

Build locally when Docker is available:

```bash
docker build \
  --file automation/execution-environment/Containerfile \
  --tag homelab-automation-ee:local \
  automation/execution-environment
docker run --rm homelab-automation-ee:local
```

Security remediation currently targets Python 3.13.16 (Debian trixie),
ansible-core 2.18.19, OpenTofu 1.13.1 and Docker CLI 29.9.0. These source pins do
not change any enrolled runner until a separately approved digest rollout.
Build candidate images with a separate tag to preserve the previous local image.
Before publication, CI scans each image and retains `security-reports/` even
when a vulnerability blocks the push. See the
[security gate and remediation evidence](../../docs/deployments/automation-image-security-2026-10-15.md).
The scanner keeps the Trivy vulnerability database in a job-scoped Docker
volume so the EE and runner scans in one job reuse the same download. A hard
20-minute start timeout prevents an unreachable vulnerability mirror from
holding a CI runner indefinitely; the scan still fails closed and produces no
publishable image.

The default container command runs `test-toolchain --run`, checking the installed
tools without needing a repository mount. Run the script without `--run` from
the source tree only when validating source-file contracts. CI explicitly loads
the repository Ansible config and tests inventory resolution inside the image.

On 2026-10-14 the local arm64 image passed its runtime check and Ansible lint;
registry publication, amd64 validation and live Semaphore execution remain
separate pending gates. Do not use the local image ID as a registry digest.

`ansible-builder.yml` is kept as the reproducible Ansible Builder definition
for operators who use `ansible-builder`. It references the same pinned Python
and Galaxy dependency files. The GitLab pipeline builds the checked-in
Containerfile directly so the published artifact has one auditable Docker
build path.

The build-time-only pip removal is implemented in that Containerfile path.
Ansible Builder users must reproduce and verify the same final runtime policy;
the alternative definition is not claimed to produce an equivalent hardened
image automatically.
