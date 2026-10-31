# Standards

Rules every app, project and change must follow.

## Standards

- [App Delivery Gates](/docs/standards/app-delivery-gates.md) — One gate guideline for every app that runs in the lab: what must be true, what evidence proves it, and who approves, from intake to retirement
- [Automation Flows](/docs/standards/automation-flows.md) — Catalog of every automated flow in the lab — app lifecycle, infrastructure, maintenance, data, security, observability, docs and DR — with trigger, automation and the only human step
- [Database Provisioning Process](/docs/standards/database-provisioning.md) — Target process for creating, rotating, adopting and retiring per-app databases, Redis users and buckets from app.yml through CI, replacing the manual and Semaphore paths
- [Domain Routing](/docs/standards/domain-routing.md) — Add, rename and remove domains for apps from one declaration, published to the Pi5 edge and the VPS gateway with verification and automatic rollback
- [Project Documentation Standard](/docs/standards/project-documentation.md) — Every project keeps two maintained docs: public-safe docs in its repo and an internal operator doc in this vault
- [Container Registry Decision](/docs/standards/registry.md) — One registry for the whole lab — GitLab Container Registry on the dedicated GitLab VM serves every image, our own and third-party; the Pi5 registry is deleted
- [Reliability Contract](/docs/standards/reliability.md) — What a green pipeline guarantees, how changes are fenced before prod, the single points of failure and the measured reliability targets
- [Secrets in 1Password](/docs/standards/secrets-1password.md) — Which 1Password vault holds which class of lab secret, the item naming and tagging pattern, who may read what, how to create and retrieve items safely, and rotation rules
