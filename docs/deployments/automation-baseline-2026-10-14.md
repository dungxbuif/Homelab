---
type: Deployment
title: "Automation host baseline"
description: "Initial active Ansible inventory and safety boundary for the homelab control plane"
timestamp: 2026-10-14T00:00:00+07:00
---

# Automation host baseline

The active automation inventory now models only three production host roles:

| Group | Host | Responsibility |
| --- | --- | --- |
| `gateway` | `vps-gateway` | public Traefik/Rathole boundary |
| `pi5_manager` | `pi5` | edge, datastore, and Swarm manager |
| `vm100_worker` | `vm100` | production application worker |

Kubernetes, kube-vip, VM `101`, and VM `102` are not present in the production
inventory. KubeKosh, if retained for study, remains an isolated application
and is not managed as a Kubernetes cluster by this control plane.

## Execution boundary

`automation/ansible/playbooks/audit.yml` is read-only. It gathers facts and
reports Docker, Swarm, swap, disk, and listening-socket state without
restarting services. `bootstrap.yml` requires an explicit
`automation_apply_baseline=true` approval and runs serially; all mutating
feature flags are false by default.

The inventory stores transport addresses only. Secrets, application endpoints,
and the dedicated backup key stay outside Git and are injected by Semaphore's
credential store or the approved secret broker.

## Verification

- Contract test: `ruby automation/ansible/tests/test-inventory-contract.rb`
- Inventory graph and syntax checks: run inside
  `homelab-automation-ee:<immutable-digest>`.
- First rollout order: audit all hosts, verify the restricted account on
  `vm100`, then Pi5, then the VPS; never apply to all hosts concurrently.
