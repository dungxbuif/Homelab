# Semaphore operator permission boundary

Live project 1 currently has only an owner membership and contains both read-only
templates (2/3/4/5) and mutating templates (1/6). No new account or role was
granted during this investigation.

## Verified limitation

The pinned v2.19.12 built-in roles are owner, manager, task_runner and guest.
Task runner has project-wide CanRunProjectTasks; guest does not. Task middleware
combines project and template permissions using bitwise OR. Thus assigning a
narrow template permission cannot remove existing project-wide run permission.
The operator plan's descriptive "Viewer" maps to guest, which can view but not
start audits. Do not claim the declarative approval YAML enforces runtime RBAC.

Current official documentation places extended/custom roles in Enterprise and
also describes their permissions as additive. Do not assume that capability is
licensed or enabled merely because the API route exists in the source.

Sources:
- [Pinned built-in role definitions](https://raw.githubusercontent.com/semaphoreui/semaphore/v2.19.12/db/ProjectUser.go)
- [Pinned task permission middleware](https://raw.githubusercontent.com/semaphoreui/semaphore/v2.19.12/api/projects/tasks.go)
- [Official roles and template permission behavior](https://semaphoreui.com/docs/user-guide/team)

## Proposed boundary, awaiting operator choice

Keep one Semaphore installation. Retain production mutations and privileged
credentials in the existing project; add a separate audit project containing
only restricted read-only templates and credentials. An audit task runner can
run all templates there without inheriting database-create or release access.
Do not copy privileged release/provisioner secrets to the audit project. Keep
existing owner access and history; do not delete or move live resources blindly.

Alternative: keep owner-only operation until another authorization boundary is
chosen. No purchase, license change, project creation, credential copy or user
creation is approved by this note. The operator question has been sent.

Acceptance after approval must include API denial tests using non-admin test
identities: audit execution allowed, production execution denied, template/key/
inventory modification denied, and guest execution denied. Passing with the
global admin is not proof. Export metadata and record rollback before mutation;
never export plaintext keys. Public application behavior is unchanged.
