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

Kubernetes is not part of the current lab. The old `iac/` Kubernetes material
is historical and must not be executed. A learning application such as
KubeKosh, if present, is not a Kubernetes cluster managed by this repository.

## Operating rule

An agent proposes a Git change or starts an approved Semaphore job. The
controlled runner performs Ansible/OpenTofu work with a restricted automation
credential, then runs post-checks and sends a sanitized status. Agents do not
receive general host SSH keys, Docker socket access, or database credentials.

## Validation

```bash
ruby automation/scripts/validate-runtime-policy.rb \
  --active automation/policies/active-runtime.yaml \
  --retired automation/policies/retired-runtime.yaml
```
