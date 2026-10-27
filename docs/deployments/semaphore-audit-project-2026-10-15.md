# Semaphore audit project deployment

Date: 2026-10-15

## Purpose

Semaphore Community's built-in `task_runner` role can run the whole project;
template permissions are additive and cannot make a mixed project read-only.
The production project therefore remains owner-only, while a second project
provides a source-backed read-only operational boundary without copying release
or provisioning credentials.

## Live resources

The idempotent bootstrap is
[`automation/semaphore/bootstrap-audit-project.mjs`](../../../../projects/homelab-legacy/automation/semaphore/bootstrap-audit-project.mjs).
It created project 2, `Homelab Audit`, with `max_parallel_tasks=1` and exactly
one member: `admin` with role `owner`.

The project contains:

- one read-only GitLab source key and repository on branch
  `codex/automation-bootstrap`;
- `Audit VM100 runtime (read only)` using the forced-command observer key;
- `Audit Pi5 runtime (read only)` using the forced-command observer key; and
- `Audit backup health (read only)` using the fixed backup-health command.

No provisioner, release, route, Docker, OpenTofu, database-provisioning or
application-deployment credential was copied. The project has no schedules.

## Verification

The source bootstrap test suite passed all four cases: dry-run does not read
credentials, apply is idempotent, resource drift aborts without deletion, and
duplicate projects abort before secret access.

Live tasks passed:

| Task | Template | Result |
|---:|---|---|
| 67 | Audit VM100 runtime (read only) | success |
| 68 | Audit Pi5 runtime (read only) | success |
| 69 | Audit backup health (read only) | success |

All three tasks checked out commit `a1848ddaf377c62c8747cb2eda8262088ede03d4`.
The bootstrap was rerun through its dry-run and live API verification; no
existing production project resource was changed.

## Remaining authorization limit

This is a project isolation boundary, not full multi-user RBAC. The only
Semaphore account is still the administrator. Adding a non-admin operator
requires a real identity and denial tests proving audit execution is allowed
while production execution and resource mutation are denied. Do not describe
the declarative role matrix as live enforcement until those tests pass.
