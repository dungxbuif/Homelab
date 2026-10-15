# Application deployment catalog

`catalog.yml` records application deployment metadata. `resources` describes
observed container limits; `{}` means no explicit container CPU/memory limits,
not unlimited physical capacity. `proposed_resources` is not an applied policy.
Do not deploy those proposals until measured and approved.

`deployable: true` means a release boundary has been enrolled. Currently only
Homepage has a verified apply template (6); other services remain running but
are not ready for automation apply. An immutable image alone is insufficient.
The deploy verifier rejects tags, unknown services, non-boolean readiness,
missing release-template IDs, missing rollback references and published ports.
It is a metadata preflight, not proof that a template still exists or permission
to run it. Authorization, exact digest enforcement and rollout verification
remain responsibilities of the enrolled release helper and Semaphore.

Observed services without a verified immutable digest remain in the catalog as
`deployable: false`; they must be reconciled from the registry before a
Semaphore apply can use them. This prevents a deployment job from silently
turning a mutable `latest` or `stable` tag into production state.
