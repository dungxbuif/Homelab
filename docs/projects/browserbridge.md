---
type: Project
title: Browser Bridge
description: Go server + Chrome MV3 extension that lets an agent drive the owner's Chrome; not deployed
generated:
  by: claude-code/opus-5.5
  at: "2026-10-31T15:00:00+07:00"
stale_after: "2027-01-29T15:00:00+07:00"
lifecycle: not deployed
project: BrowserBridge
class: none
owner: dungxbuif
repo: dungxbuif/browserbridge
deployed_revision: n/a
---

# Browser Bridge

## Summary

Personal project: an AI agent / MCP client talks to a Go server, and a Chrome MV3 extension connects back over WSS to expose tabs, CDP, DOM, screenshots and media fetch. Has a `docker-compose.yml` for local use.

Class `none` · owner dungxbuif · status `not deployed`.

## Source

| Field | Value |
|---|---|
| Local checkout | `/home/dungxbuif/workspace/projects/BrowserBridge/` |
| GitLab | `dungxbuif/browserbridge` (published branch `codex/workspace-unreleased-20261028`) |
| Repo docs | `README.md`, `docs/`, `IDEAL_SPEC.md` |
| Deployed revision | n/a |

## Why it does not run

Personal local tool; no lab stack or route. A Google OAuth client-secret JSON sits in the checkout root (gitignored by `**/*secret*.json`, not tracked) — keep it out of any image.
