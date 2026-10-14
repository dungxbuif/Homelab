# Homelab automation execution environment

This is the single pinned toolchain for infrastructure jobs. Semaphore and
GitLab CI should use the image built from `Containerfile` with the immutable
`$CI_COMMIT_SHA` tag and the digest returned after push. A mutable tag is not a
production executor reference.

The image contains:

- pinned `ansible-core`, `ansible-lint`, `yamllint`, and required collections;
- OpenTofu and Docker CLI binaries from pinned image tags;
- ShellCheck, Ruby, `jq`, and SSH client for policy and route validation.

Build locally when Docker is available:

```bash
docker build \
  --file automation/execution-environment/Containerfile \
  --tag homelab-automation-ee:local \
  automation/execution-environment
docker run --rm homelab-automation-ee:local
```

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
