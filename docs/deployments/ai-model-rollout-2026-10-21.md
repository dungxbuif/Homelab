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
| `mypocket-worker` | `DeepSeek-V4.1-Flash` | Updated on the Pi5 Swarm manager |
| OmniScan source template | `qwen/qwen3.6-35b-a3b` | Updated production template and docs |

The MyPocket local MLX example remains a local-development profile, not a
production credential-backed service.

The source credential map is now aligned as well: `OMNISCAN_SECRETS.LLM_MODEL`
and `MYPOCKET_SECRETS.AI_MODEL` in `local_vars.json` both select
`DeepSeek-V4.1-Flash`. This changes selectors only; endpoint and credential
values are untouched.

The repeatable read-only audit is installed on VM100 as
`/usr/local/lib/homelab-maintenance/audit-ai-models.sh`. The post-release live
audit reports all five selectors as compliant, including `mypocket-worker`.
The MyPocket health endpoint also returned HTTP `200` after the rolling update.

## Deployment boundary

`mypocket-worker` is a Swarm service managed from Pi5. VM100 is a worker and
cannot mutate the service spec. The approved manager-side release command
changed only `AI_MODEL`, used the existing `start-first` policy, and recorded a
mode-0600 rollback receipt. No worker image or endpoint was changed.

The manager-side command completed with Docker's `update completed` result and
the replacement worker task is running with the expected selector.

## Verification

1. Contract tests for the fixed release command pass.
2. The live model audit passes all five selectors.
3. The replacement worker task is running after the rolling update.
4. `https://money.dungxbuif.com/api/v1/health` returned HTTP `200`.

Remaining work is business-quality UAT for representative MyPocket inference;
the selector rollout itself is complete. The repository's synthetic evaluation
pack was also verified on 2026-10-21 with:

```text
go test ./internal/usecase -run 'Test(AIEvalFixtures|AdvisorReliabilityFixtureSchema|AdvisorReview)' -count=1
ok
```

This proves deterministic safety and reliability boundaries only. The opt-in
live provider matrix remains separate and must use synthetic input plus an
approved UAT receipt before the quality item can close.

## Live quality follow-up

The first live matrix found one defect: after a `not_found` finance result,
the provider attempted an unrelated wallet lookup. MyPocket commit
`23ecdca` now treats an all-`not_found` read batch as terminal and refuses to
dispatch an unexpected follow-up tool. The regression test and deterministic
suite pass, and the rerun of `TestLiveAdvisorQualityMatrix` passed all six
synthetic cases in about 77 seconds: period, follow-up, missing data,
unsupported banking, prompt injection and review-only proposal.

The live run used no production database, ledger, confirmation endpoint or
user data. This closes the model-routing/safety verification gate; owner-level
business UAT remains separate. The MyPocket commit is present locally, but its
GitHub push was rejected because the remote repository reported a missing
historical object; no force-push or history rewrite was attempted.
