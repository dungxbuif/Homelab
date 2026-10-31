---
type: Reference
title: "Vault Document Conventions (OKF)"
description: "Frontmatter and linking conventions used in this vault, based on the external Open Knowledge Format"
timestamp: 2026-10-31T12:00:00+07:00
---

# Vault Document Conventions

This vault loosely follows the external
[Open Knowledge Format specification](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md).
The local copy of the v0.1 draft was removed; read the upstream spec for
details.

## Conventions used here

- Markdown files with YAML frontmatter:

  ```yaml
  ---
  type: Dashboard | Reference | Playbook | Deployment Evidence | Plan
  title: "Human title"
  description: "One sentence"
  timestamp: 2026-10-31T12:00:00+07:00
  ---
  ```

- Update `timestamp` whenever content changes.
- Use relative links between docs; link only to files that exist.
- Current-state pages (STATUS, STACK, host refs) describe now. Dated
  deployment records are evidence for one change. History lives in git.
- Never write secret values; record names and locations only.
