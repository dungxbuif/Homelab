---
type: DeploymentEvidence
title: "Workspace layout normalization"
description: "Move project checkouts under projects and remove homelab source trees from the knowledge vault"
timestamp: 2026-10-28T00:00:00+07:00
---

# Workspace layout normalization — 2026-10-28

The workspace now separates source checkouts from vaults:

- Project checkouts live under `/home/dungxbuif/workspace/projects/`.
- Vaults live under `/home/dungxbuif/workspace/vaults/`.
- `/home/dungxbuif/workspace/projects/homelab-ops/` is the canonical active
  homelab automation repository.
- The former homelab source trees are retained at
  `/home/dungxbuif/workspace/projects/homelab-legacy/` for rollback and
  migration history only.

The `homelab` vault keeps documentation, operational evidence, rules, and
references. No production deployment or credential was changed by this layout
move.
