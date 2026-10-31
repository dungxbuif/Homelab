---
type: Project
title: apps (stray folder)
description: Loose folder holding a copy of the db-management web package; not a project of its own
generated:
  by: claude-code/opus-5.5
  at: "2026-10-31T15:00:00+07:00"
stale_after: "2027-01-29T15:00:00+07:00"
lifecycle: not deployed
project: apps
class: none
owner: dungxbuif
repo: (not a Git repo)
deployed_revision: n/a
---

# apps (stray folder)

## Summary

Not a Git repository. It contains a single file, `apps/web/package.json`,
for the package `@db-management/web`. It looks like a stray fragment of the
[db-management](./db-management.md) monorepo layout (unverified how it got here).

## Source

| Field | Value |
|---|---|
| Local checkout | `/home/dungxbuif/workspace/projects/apps/` |
| GitLab | none |
| Repo docs | none |
| Deployed revision | n/a |

## Why it does not run

Nothing here is deployed. The running `db-management_web` service on VM110 is
built from the `db-management` repo, not from this folder. Delete candidate
once confirmed nothing references it.
