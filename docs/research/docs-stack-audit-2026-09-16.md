# Homelab documentation and stack audit - 2026-09-16

## Scope and intended changes

Documentation-only audit requested by the operator. Canonical infrastructure
repository: `/home/dungxbuif/workspace/vaults/homelab`. The separate
`/Users/dungxbuif/Documents/ChatGPT/Homelab` workspace contains RelayHub
documentation/research; it is not the deployed infrastructure inventory.
Do not deploy, change credentials, delete service data, or alter networks.

Affected surfaces: root `index.md`, `docs/INDEX.md`, host runbooks,
`docs/MAIN.md`, network audit, and changelog. Preserve superseded topology
in `docs/archived/`; label dated deployment/research notes rather than
silently treating historical measurements as current.

Correct stale VM100 host-port routing, distinguish MyPocket's unmoved dev
checkout from its deployed production services, restore Proxmox's production
hypervisor role, and document GitLab's three isolated VPS tunnels and Registry
trial separately from the shared Orange Pi edge. Mac roaming via NetBird is
proposed only. Publish a concise Markdown current-stack catalog and `llms.txt`
entry point for human/agent navigation without exposing secrets.

## Verification plan

- Read tracked/untracked manifests and existing deployment evidence.
- Probe hosts through SSH where available; log coverage and failure, not
  inferred health. Inspect only secret-free runtime fields.
- Validate Markdown relative file links in the current core docs, excluding
  intentionally historical archive links and external URLs.
- Validate the Markdown/llms.txt agent surface and whitespace. Reconcile the final catalog
  against evidence; retain unverified state and open maintenance items.

## Findings and result

### Documentation reconciliation

- Added `docs/STACK.md` as the current human/agent inventory and root
  `llms.txt` as its navigation surface; refreshed root index and core runbooks.
- Preserved the old root index, MAIN playbook and AWS-only Proxmox guide
  under `docs/archived/superseded-topology/`, with archive-index links.
- Corrected Proxmox's production role, retired VM100 host-port routing,
  MyPocket production versus unmoved development checkout, and GitLab's
  isolated HTTPS/SSH/Registry tunnels versus the shared Orange Pi edge.
- Marked network segmentation and Mac roaming as proposals, not deployed
  behavior. Distinguished Registry trial from the retained Pi5 Registry.
- Repaired historical changelog file links and labeled dated preflight
  measurements. Added a README in the supplied documentation workspace
  pointing to the canonical infrastructure repository; no folders moved.

### Runtime evidence

- VM100 direct-key SSH succeeded: 16 Swarm task containers and 2 standalone
  BDS containers running. Healthchecks and bootstrap limitations are listed
  in STACK.md; this is not end-to-end application acceptance.
- BDS inspection confirmed no host port bindings; app networks are
  `bds-tunnel-net` and `homelab-net`, connector only `bds-tunnel-net`.
- VM100 guest: 15 GiB reported RAM, about 5.1 GiB used; root filesystem
  194 GiB total, 65 GiB used, 130 GiB available; swap zero. Samples are
  point-in-time, not peak-load capacity measurements.
- Public HTTPS probes forced the VPS address with certificate verification:
  homepage, n8n health, RelayHub health, GitLab sign-in and NetBird dashboard
  returned 200; both Registry endpoints returned the expected 401 challenge.
  RelayHub readiness returned 503, consistent with its bootstrap-only state.
- Pi5 and VPS direct-key SSH failed authentication; Orange Pi SSH timed out
  before its banner. Their inventory remains based on deployment records,
  not fresh host inspection. This does not establish host/service failure.

### Verification and limits

- Relative Markdown file links passed across 40 current documents, including
  the archive index; code-fence examples and historical snapshot links were
  excluded. External URLs and section anchors were not exhaustively checked.
- `git diff --check` passed. The new agent surface is plain Markdown and
  `llms.txt`; public hosting was not changed or claimed.
- No runtime, secrets, application code, data, source checkout placement or
  network configuration changed. Existing unrelated worktree changes remain.
- RelayHub public/API documentation needs no change: this audit changes
  infrastructure documentation/navigation, not RelayHub behavior or API.
- Follow-ups remain operational work, not completed by this audit: restore
  admin SSH coverage, resolve GitLab split DNS/edge cutover, validate
  authenticated app/Git/Registry workflows and off-host backup restore,
  measure resources under load, and review broad shared-network access.
