---
type: Deployment
title: "AI model audit and DeepSeek-V4.1-Flash rollout"
description: "Audit of runtime model selectors across VM100 and application templates"
timestamp: 2026-10-21T03:00:00+07:00
---

# AI model audit and rollout

## Intended behavior

Production services that use the shared DeepSeek credential select
`DeepSeek-V4.1-Flash`. Credentials remain runtime-only and are never copied to
the repository or emitted in audit output.

## Audit result

The VM100 container audit found:

| Service | Observed model | Action |
|---|---|---|
| `openclaw` | `DeepSeek-V4.1-Flash` | Already compliant |
| `whiteboard-backend` | `DeepSeek-V4.1-Flash` for fast/reasoning | Already compliant |
| `mypocket-api` | `DeepSeek-V4.1-Flash` | Already compliant |
| `mypocket-worker` | `qwen/qwen3.6-35b-a3b` | Requires Swarm service update |
| OmniScan source template | `qwen/qwen3.6-35b-a3b` | Updated production template and docs |

The MyPocket local MLX example remains a local-development profile, not a
production credential-backed service.

The source credential map is now aligned as well: `OMNISCAN_SECRETS.LLM_MODEL`
and `MYPOCKET_SECRETS.AI_MODEL` in `local_vars.json` both select
`DeepSeek-V4.1-Flash`. This changes selectors only; endpoint and credential
values are untouched.

The repeatable read-only audit is installed on VM100 as
`/usr/local/lib/homelab-maintenance/audit-ai-models.sh`. Its first live run
confirmed three compliant services and one mismatch: `mypocket-worker` still
reports `qwen/qwen3.6-35b-a3b`.

The follow-up audit on 2026-10-21 confirmed the same result after source
configuration reconciliation. Backup units were healthy and VM100 had `39G`
free, so the model mismatch is isolated from the current backup and capacity
state.

## Deployment boundary

`mypocket-worker` is a Swarm service managed from Pi5. VM100 is a worker and
cannot mutate the service spec. The Pi5 SSH endpoint currently resets the SSH
key exchange, so the production worker update is pending manager access. No
worker restart or speculative change was made from VM100.

Semaphore task `#139` was also tested as the controlled manager path. The
playbook reached the Pi5 approval assertion, then failed at the first remote
installation task with `UNREACHABLE`; this confirms the issue is the Pi5
transport/SSH path rather than the model-update playbook. No retry loop was
left running.

## Verification plan

1. Read the manager service spec and record the current image/update policy.
2. Apply only `AI_MODEL=DeepSeek-V4.1-Flash` with the existing rolling-update policy.
3. Verify the replacement worker environment, health, logs, and MyPocket API
   smoke path.
4. Record the result and rollback command in this document.
