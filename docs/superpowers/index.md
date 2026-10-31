# Plans and design specs

## Plans

- [Compute Layout and Resource Sizing](/docs/superpowers/plans/2026-10-31-compute-layout-and-sizing.md) — Three-VM layout (prod, GitLab, backup) plus Pi5, sized from measured usage on 2026-10-31, with the re-allocation steps and capacity checks
- [GitLab Production Task: IaC VMs, Safe Migration, Verified Drive Backups](/docs/superpowers/plans/2026-10-31-gitlab-production-task.md) — Task spec to make GitLab production-grade: all VMs under OpenTofu, migrate GitLab to its own VM without losing data, native scheduled backups to Google Drive that verify themselves and leave no junk when they fail
- [GitLab Protection, Dedicated VM and Registry Consolidation](/docs/superpowers/plans/2026-10-31-gitlab-protection-and-registry-consolidation.md) — Make GitLab recoverable with verified off-site backups, move it to its own VM, keep the registry on the GitLab VM disk and delete the Pi5 registry
- [Lab-wide IaC Automation Rebuild](/docs/superpowers/plans/2026-10-31-lab-iac-automation-rebuild.md) — Fresh audit of the current lab and a from-scratch plan to manage every layer (network, hypervisor, hosts, edge, data, apps, secrets, CI/CD, DR) as code in homelab-ops
- [RelayHub Collaboration and Release Implementation Plan](/docs/superpowers/plans/2026-10-31-relayhub-centrifugo-collaboration.md) — 
- [RelayHub Centrifugo Foundation Implementation Plan](/docs/superpowers/plans/2026-10-31-relayhub-centrifugo-foundation.md) — 
- [RelayHub Durable Rooms Implementation Plan](/docs/superpowers/plans/2026-10-31-relayhub-centrifugo-rooms.md) — 
- [RelayHub Full Webhooks Implementation Plan](/docs/superpowers/plans/2026-10-31-relayhub-full-webhooks.md) — 
- [RelayHub Product Docs and Developer Kit Implementation Plan](/docs/superpowers/plans/2026-10-31-relayhub-product-docs.md) — 

## Design specs

- [RelayHub realtime: Centrifugo and SDK forks](/docs/superpowers/specs/2026-10-31-relayhub-centrifugo-fork-design.md) — 
- [RelayHub full webhook restoration](/docs/superpowers/specs/2026-10-31-relayhub-full-webhooks-design.md) — 
- [RelayHub product documentation and Developer Kit](/docs/superpowers/specs/2026-10-31-relayhub-product-docs-design.md) — 
