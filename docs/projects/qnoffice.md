---
type: Project
title: QN Office
description: Quy Nhon office management portal + Mezon bot (Nx monorepo); not deployed in the lab
generated:
  by: claude-code/opus-5.5
  at: "2026-10-31T15:00:00+07:00"
stale_after: "2027-01-29T15:00:00+07:00"
lifecycle: not deployed
project: QnOffice
class: none
owner: dungxbuif
repo: dungxbuif/qnoffice
deployed_revision: n/a
---

# QN Office

## Summary

Office-operations system for the Quy Nhơn office: web portal and Mezon bot (pantry, transactions on Dong.mezon, etc.). Nx monorepo with `terraform/` and `.gcloudignore` (GCP target). Upstream origin `tiennguyenvan-ncc/QnOffice`.

Class `none` · owner dungxbuif · status `not deployed`.

## Source

| Field | Value |
|---|---|
| Local checkout | `/home/dungxbuif/workspace/projects/QnOffice/` |
| GitLab | `dungxbuif/qnoffice` (published branch `production`) |
| Repo docs | `README.md`, `docs/` |
| Deployed revision | n/a |

## Why it does not run

Runs outside the lab (GCP target per repo, unverified). An old compose lives in `selfhost/docker/qn-office/`; no current lab service.
