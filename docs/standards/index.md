# Standards

Rules every app, project and change must follow.

## Standards

- [App Delivery Gates](/docs/standards/app-delivery-gates.md) — One gate guideline for every app that runs in the lab: what must be true, what evidence proves it, and who approves, from intake to retirement
- [Automation Flows](/docs/standards/automation-flows.md) — Catalog of every automated flow in the lab — app lifecycle, infrastructure, maintenance, data, security, observability, docs and DR — with trigger, automation and the only human step
- [Database Provisioning Process](/docs/standards/database-provisioning.md) — Target process for creating, rotating, adopting and retiring per-app databases, Redis users and buckets from app.yml through CI, replacing the manual and Semaphore paths
- [Project Documentation Standard](/docs/standards/project-documentation.md) — Every project keeps two maintained docs: public-safe docs in its repo and an internal operator doc in this vault
- [Container Registry Decision](/docs/standards/registry.md) — GitLab Container Registry is the single lab registry with its storage on RustFS (Pi5); the Pi5 registry becomes a pull-through mirror for tier-1 images
