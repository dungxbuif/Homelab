# Application deployment catalog

`catalog.yml` is the allow-list for application deployments. A service is
deployable only when its image, private networks, health path, resource limit,
route IDs, and rollback image are declared. The deploy verifier rejects tags,
unknown services, missing rollback references, and host-published ports.

Observed services without a verified immutable digest remain in the catalog as
`deployable: false`; they must be reconciled from the registry before a
Semaphore apply can use them. This prevents a deployment job from silently
turning a mutable `latest` or `stable` tag into production state.
