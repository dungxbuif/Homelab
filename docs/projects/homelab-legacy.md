---
type: Project
title: homelab-legacy
description: Retained snapshot of the old homelab source tree moved out of the vault on 2026-10-28; retiring
status: deprecated
generated:
  by: claude-code/opus-5.5
  at: "2026-10-31T15:00:00+07:00"
stale_after: "2027-01-29T15:00:00+07:00"
lifecycle: retired
project: homelab-legacy
class: none
owner: dungxbuif
repo: (not a Git repo)
deployed_revision: n/a
---

# homelab-legacy

## Summary

Retained snapshot of the source tree moved out of the `vaults/homelab` vault
on 2026-10-28 (`automation`, `backup`, `deprecated`, `edge-registrar`,
`goclaw`, `iac`, `kubernetes`, `migration`, `monitoring`, `relayhub`). Kept
for migration history and rollback only. It is being retired.

## Source

| Field | Value |
|---|---|
| Local checkout | `/home/dungxbuif/workspace/projects/homelab-legacy/` |
| GitLab | none |
| Repo docs | `README.md` (states: do not deploy from this tree) |
| Deployed revision | n/a |

## Why it does not run

Superseded by [homelab-ops](./homelab-ops.md). Do not deploy from it. Remove
after the H→O migration and consumer cutover are accepted.
