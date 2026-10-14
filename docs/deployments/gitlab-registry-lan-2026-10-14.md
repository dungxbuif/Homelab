# GitLab registry LAN route

Observed: public VPS ingress returns the proper registry 401 Bearer challenge,
but LAN wildcard DNS directs the hostname to Pi5 whose config lacks this route.
The existing GitLab LAN service already uses `tasks.gitlab_gitlab:80`.

Add one router/service pair named `gitlab-registry`, hostname
`registry-gitlab.dungxbuif.com`, backend `http://tasks.gitlab_gitlab:5005`.
Reuse the existing GitLab router TLS configuration, preserving all other routes.
The Pi5 registry hostname `registry.dungxbuif.com` is unchanged.

Traefik bind-mounts a single file. Publication must preserve its inode so the
container observes new content. Validate YAML first, retain the original in a
private backup, write/fsync the existing inode, and require a valid HTTPS 401
plus the registry API header. On failure, restore the original file in place.
No Traefik restart or production container rollout is intended.

This is bootstrap remediation; the general catalog publisher is not yet live.
After success, reconcile the route catalog and avoid running its incomplete
generated config over the live file. Public behavior was already present;
this fixes the same endpoint for LAN users and CI.

## Verified outcome

Live Ansible apply completed with failed=0. The Pi5 HTTPS probe and a separate
Mac LAN request both return 401, `Docker-Distribution-Api-Version: registry/2.0`,
and the GitLab JWT Bearer realm. TLS verification stayed enabled. The source
dynamic config and route catalog now include the narrow addition. Other dirty
source routing changes remain untouched. The publisher's inode/idempotence and
invalid-input preservation tests passed. The live file was updated without
restarting Traefik. Each run creates its own private rollback snapshot so a later
failure cannot restore an obsolete baseline over unrelated route changes.
