# Homelab Automation

This directory is the active automation boundary for the homelab. It is
Git-backed and executed through the private Semaphore control plane.

## Source of truth

- `policies/active-runtime.yaml` contains only active hosts, services, routes,
  networks, and backup classes. It contains no secret values.
- `policies/retired-runtime.yaml` records historical targets that must never be
  loaded by a production inventory.
- `ansible/` will own host configuration and service orchestration.
- `tofu/` will own Proxmox VM lifecycle only.
- `routes/` will own the structured route catalog and generated edge files.
- `stacks/` will own validated Swarm/Compose deployment definitions.
- `execution-environment/` is the pinned toolchain used by infrastructure
  jobs. Its immutable image contains Ansible, OpenTofu, Docker CLI, ShellCheck,
  YAML validation, and the required Galaxy collections.

Kubernetes is not part of the current lab. The old `iac/` Kubernetes material
is historical and must not be executed. A learning application such as
KubeKosh, if present, is not a Kubernetes cluster managed by this repository.

## Operating rule

An agent proposes a Git change or starts an approved Semaphore job. The
controlled runner performs Ansible/OpenTofu work with a restricted automation
credential, then runs post-checks and sends a sanitized status. Agents do not
receive general host SSH keys, Docker socket access, or database credentials.

GitLab CI builds the execution image with the commit SHA as its tag and reports
the pushed registry digest. Production templates must reference that digest,
never a mutable tag. The pipeline validates active YAML, shell syntax, the
runtime policy, Ansible lint, OpenTofu formatting when a module exists, and
tracked-file secret patterns before publishing the image.

The local toolchain smoke test is:

```bash
docker build \
  --file automation/execution-environment/Containerfile \
  --tag homelab-automation-ee:local \
  automation/execution-environment
docker run --rm homelab-automation-ee:local --run
```

## Validation

```bash
ruby automation/scripts/validate-runtime-policy.rb \
  --active automation/policies/active-runtime.yaml \
  --retired automation/policies/retired-runtime.yaml
```
