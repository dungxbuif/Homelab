# Runtime audit evidence gate

## Intent

Declarative policy export must not imply live health. Change its status to
`not_verified`. Inventory drift accepts only `mode: observed`, `status: ok`,
`complete: true`, a timezone-aware `observed_at` no older than 15 minutes,
and explicit unique string lists for hosts, services and routes.
Reject malformed, partial, future-dated and declarative evidence with exit 2.
Exit 1 means inventory drift; exit 0 means only inventory IDs match, not
resource health or verified backups. The collector is still pending.

Verification: CLI regression tests for policy export, invalid evidence,
fresh matching inventory and genuine drift. No runtime services are changed.
Public application documentation is unaffected by this internal gate.

## Verified result

The old CLI accepted declarative and stale reports with exit 0. Regression
tests reproduced that behavior before the fix. After implementation, all 15
tests under `automation/tests` pass in `homelab-automation-ee:local`.
The evidence test is included in GitLab validation. No live collector or
production-health certification is claimed by this change.
