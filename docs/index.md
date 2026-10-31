# Homelab documentation map

Read in this order: overview → STATUS → STACK → host, project or service doc → runbook.

## Current state

- [Overview and operating rules](/docs/overview.md) — code ownership, topology, constraints.
- [STATUS](/docs/STATUS.md) — one-page status and open gates.
- [STACK](/docs/STACK.md) — hosts, workloads, network, datastores, backups.
- [BACKLOG](/docs/BACKLOG.md) — open work only, mapped to plan phases.
- [Standing decisions](/docs/decisions.md) — architecture decisions still in force.
- [MAIN](/docs/MAIN.md) — ingress topology and service publishing playbook.

## Hosts

- [Pi5](/docs/PI.md) — edge, Swarm manager and datastores.
- [VM100](/docs/VM100.md) — production compute.
- [Proxmox](/docs/PROXMOX.md) — hypervisor for VM100 and VM110.
- [Mac](/docs/MAC.md) — native OCR and LM Studio.
- [MikroTik](/docs/MIKROTIK.md) — router (DHCP DNS needs urgent verification).
- [Proxmox prerequisites](/docs/PRE_REQUIRE.md) — API token and SSH checklist for IaC.

## Projects and services

- [Projects](/docs/projects/index.md) — one internal doc per project checkout, deployed first.
- [Services](/docs/services/index.md) — platform and third-party services (GitLab, n8n, NetBird, Databasus …).
- [Project workspace inventory](/docs/PROJECTS.md) — checkout paths and GitLab mirrors.
- [CouchDB Obsidian sync](/docs/COUCHDB_OBSIDIAN_SYNC.md) — LiveSync database runbook.

## Standards

- [Standards](/docs/standards/index.md) — delivery gates, project docs, database provisioning, registry.
- [Vault knowledge format](/docs/OKF_SPEC.md) — OKF v0.2 profile for every doc in this vault.

## Runbooks and evidence

- [Runbooks](/docs/runbooks/index.md) — backup/restore, DB provisioning, secrets, GitLab Redis, vault protection.
- [Deployment evidence](/docs/deployments/index.md) — 2026-10-31 records that back the current runtime.
- [Update log](/docs/log.md) — newest first.

## Plans

- [Plans and specs](/docs/superpowers/index.md) — the IaC automation rebuild plan and RelayHub plans.

## Diagrams

- Current: [system overview](/docs/assets/diagrams/system-overview.svg), [what runs where](/docs/assets/diagrams/hosts-workloads.svg), [ingress and domains](/docs/assets/diagrams/ingress-domains.svg), [data and backup](/docs/assets/diagrams/data-and-backup.svg), [VPS gateway](/docs/assets/diagrams/vps-gateway.svg), [NetBird relay](/docs/assets/diagrams/netbird-relay.svg), [upgrade and restore](/docs/assets/diagrams/upgrade-and-restore-flow.svg), [project reference flow](/docs/assets/diagrams/project-reference-flow.svg)
- Standards: [automation flows](/docs/assets/diagrams/automation-flows.svg), [delivery gates](/docs/assets/diagrams/app-delivery-gates.svg), [two docs per project](/docs/assets/diagrams/project-docs-sync.svg), [database provisioning](/docs/assets/diagrams/db-provisioning.svg)
- Plan: [IaC ownership](/docs/assets/diagrams/iac-target-architecture.svg), [execution](/docs/assets/diagrams/iac-execution.svg), [app CI/CD](/docs/assets/diagrams/app-cicd-flow.svg), [golden path](/docs/assets/diagrams/app-golden-path.svg), [access model](/docs/assets/diagrams/access-model.svg), [roadmap](/docs/assets/diagrams/iac-roadmap.svg)
