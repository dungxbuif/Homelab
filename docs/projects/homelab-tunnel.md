---
type: Project
title: Homelab Tunnel
description: Design specs for an FRP-based service registration and tunnel system; no code, not deployed
generated:
  by: claude-code/opus-5.5
  at: "2026-10-31T15:00:00+07:00"
stale_after: "2027-01-29T15:00:00+07:00"
lifecycle: not deployed
project: homelab-tunnel
class: none
owner: dungxbuif
repo: (not a Git repo)
deployed_revision: n/a
---

# Homelab Tunnel

## Summary

Specs for one codebase that registers services and forwards traffic through
managed FRP tunnels, with separate LOCAL (LAN via Orange Pi) and PUBLIC
(ngrok-like via VPS and wildcard DNS) trust boundaries. Contents are
`README.md` and `docs/specs/{LOCAL,PUBLIC}.md` only.

## Source

| Field | Value |
|---|---|
| Local checkout | `/home/dungxbuif/workspace/projects/homelab-tunnel/` |
| GitLab | none (no Git repo) |
| Repo docs | `README.md`, `docs/specs/` |
| Deployed revision | n/a |

## Relation to running services

Not deployed, and no code exists. The lab uses **Rathole**, not FRP, for the
same job: VPS `rathole-server` ↔ Pi5 `edge-rathole-pi5`, plus the GitLab and
Mac tunnels (see [STACK.md](../STACK.md)). The LOCAL spec assumes the Orange
Pi edge, which is down and retired. Treat this as a design idea; it would
need to be re-scoped against the current Pi5 edge before any work.
