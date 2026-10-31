---
type: Playbook
title: Proxmox IaC Prerequisites
description: "What OpenTofu/Ansible in homelab-ops need from Proxmox: API token, SSH access, tooling"
generated:
  by: claude-code/opus-5.5
  at: "2026-10-31T12:00:00+07:00"
stale_after: "2027-01-29T12:00:00+07:00"
---

# Proxmox IaC Prerequisites

The old Kubernetes-era Terraform guide (VM template 9000, `iac/terraform`) is
obsolete and was removed; it is in git history. IaC code now lives in
`/home/dungxbuif/workspace/projects/homelab-ops`, and the forward design is the
[IaC automation rebuild plan](./superpowers/plans/2026-10-31-lab-iac-automation-rebuild.md).

## Needed before any OpenTofu run against Proxmox (`10.10.0.20`)

1. **Dedicated API token.** A PVE user (not `root@pam`) with a role limited to
   the VMs it manages; store token ID and secret in 1Password, never here. No
   such token is currently documented (unverified whether one exists).
2. **SSH access.** As of 2026-10-31 there is no recorded SSH alias or
   credential for Proxmox; agents hit `Too many authentication failures`.
   Add a dedicated key and an `~/.ssh/config` alias with `IdentitiesOnly yes`.
3. **Tooling** on the control machine: OpenTofu and Ansible (versions pinned
   by `homelab-ops`).
4. **Safety.** VM100 (ID 100) and VM110 (ID 110) are production. Import only,
   with destroy protection; never apply a plan that recreates them. Audit the
   hypervisor before any cleanup.
