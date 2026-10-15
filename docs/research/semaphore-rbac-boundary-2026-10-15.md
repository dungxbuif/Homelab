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

## Community boundary decision

Keep one Semaphore installation. Retain production mutations and privileged
credentials in the existing project; add a separate audit project containing
only restricted read-only templates and credentials. An audit task runner can
run all templates there without inheriting database-create or release access.
Do not copy privileged release/provisioner secrets to the audit project. Keep
existing owner access and history; do not delete or move live resources blindly.

The operator approved completion of the safe Community-edition boundary without
inventing fine-grained roles. The source-backed bootstrap creates a separate
`Homelab Audit` project owned by the existing administrator. It contains only
the read-only GitLab source checkout, fixed-command host audits for VM100 and
Pi5, and the combined read-only backup-health template.

The audit project receives only the read-only source, host-observer, and
backup-health credentials. It receives no provisioner, release, route, Docker,
OpenTofu, database-provisioning, or application-deployment credential. The
bootstrap is idempotent and fails on duplicate names or resource drift; it does
not delete or mutate the existing production project. The single admin account
remains the only member until a real non-admin identity and a separate denial
test plan are supplied. This is an isolation boundary, not proof of multi-user
RBAC.

Acceptance after approval must include API denial tests using non-admin test
identities: audit execution allowed, production execution denied, template/key/
inventory modification denied, and guest execution denied. Passing with the
global admin is not proof. Export metadata and record rollback before mutation;
never export plaintext keys. Public application behavior is unchanged.
