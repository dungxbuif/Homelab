# Homelab Automation Control Plane Specification

## Scope

The active lab consists of the VPS public boundary, Pi5 edge/datastore/Swarm
manager, VM100 production worker, Proxmox VM100 lifecycle, and explicit Mac
native-service exceptions. Kubernetes is not an active lab platform.

## Invariants

1. Active inventory contains no Kubernetes host, node, API, kube-vip address,
   or cluster resource.
2. Historical IaC remains available for reference but is not executable by
   active automation.
3. No secret values are stored in the runtime catalog.
4. Database/cache/backup services cannot receive public routes.
5. Every managed service references an active host and declared network.
6. OpenTofu manages Proxmox resources only; Ansible manages host and service
   configuration.

## Verification contract

The runtime policy validator must reject duplicate identifiers, historical
targets in active inventory, unknown service references, unsupported exposure
values, protected data routes, and Kubernetes targets. A valid catalog must
produce an `ok` report with zero errors and zero Kubernetes targets.
