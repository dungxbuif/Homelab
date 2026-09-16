# Temporary GitLab VPS HTTPS Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Serve GitLab HTTPS publicly through an isolated VM100/VPS tunnel while Orange Pi SSH is unavailable.

**Architecture:** A new VPS Rathole server accepts a Noise client from VM100 and exposes GitLab HTTP only on VPS Docker `gateway-network`. VPS Traefik Docker labels create the HTTPS router; removing one GitLab term from the VPS TCP passthrough rule lets that router handle GitLab SNI.

**Tech Stack:** Docker Compose/Swarm, Rathole, Traefik v3.6, Python 3.12/PyYAML.

**Spec:** [Temporary GitLab VPS HTTPS Route](../specs/2026-09-15-gitlab-vps-https-temporary.md)

## Global Constraints

- Preserve existing Orange Pi, VPS `7000` HTTPS, and VPS `7001`/`:2222` Git SSH tasks.
- VM100 client and GitLab remain portless on `homelab-net`; VPS server joins only `gateway-network`.
- Token and Noise private key never enter the repo or final answer.
- Backup and hash-check VPS dynamic YAML; alter only its GitLab HostSNI term in place.
- Keep public docs plus agent-readable service facts reconciled with runtime.

---

### Task 1: New HTTP tunnel source and preflight

**Files:** Create `migration/gitlab-https-tunnel/{docker-compose.yml,client-stack.yml,server.toml.template,client.toml.template}`. Reuse `migration/gitlab-ssh-tunnel/render-runtime.py` on VPS.

- [x] Add Compose server pinned to the current Rathole digest, external `gateway-network`, host `7002:7002`, no host `8085`, a 128 MiB/0.5 CPU envelope, and labels for the GitLab HTTPS router/upstream port.
- [x] Add VM100 Swarm client pinned to the same digest, external `homelab-net`, secret-mounted TOML, no published port, 128 MiB/0.5 CPU limit.
- [x] Add Noise/token templates with `7002`, Docker DNS `tasks.gitlab_gitlab:80`, and VPS static tunnel endpoint.
- [x] Run `docker compose config -q`, `docker stack config`, and parsed template assertions; verify VPS `7002` free and `gateway-network` exists.

### Task 2: Stand up backend without touching shared ingress

**Files:** Deploy source files to VPS `/root/gitlab-https-tunnel/`; client source/secret to Pi5 `/ssd-data/infra/gitlab/`.

- [x] Render runtime on VPS using the shared renderer, confirm TOML, token match, Noise keys, mode/ownership without printing secrets.
- [x] Start only the new VPS Compose project and verify image process, `7002` control port, label set, and backend `8085` network-only.
- [x] Create Pi5 Swarm secret, deploy only the new VM100 client, and verify its control channel plus direct GitLab login through VPS Docker network.
- [x] If the isolated tunnel fails, remove it without editing VPS dynamic YAML (failure contingency was not invoked).

### Task 3: Cut over only GitLab SNI

**Files:** Create `migration/gitlab-https-tunnel/patch_gateway.py` and focused tests. Modify VPS `/root/gateway/dynamic.yml` only after Task 2 passes.

- [x] Write parser-backed tests for exactly one GitLab HostSNI removal, preservation of every other token/object, missing/duplicate input rejection, and in-place backup/restore.
- [x] Implement a guarded, hash-checked, in-place patch that preserves the bind-mounted inode; keep a mode-preserving timestamped backup.
- [x] Run tests, inspect dry-run diff, apply to VPS, and observe Traefik reload/ACME logs.
- [x] Verify public certificate, login 200/assets, Git SSH fingerprint, and existing domains; restore backup in place if any gateway regression appears (none observed).

### Task 4: Reconcile operations docs

**Files:** Modify `docs/services/gitlab.md`, `docs/MAIN.md`, `docs/VM100.md`, `docs/LOG.md`, `migration/README.md`, and GitLab research/plan notes.

- [x] Record temporary VPS HTTPS live status and agent-readable facts; retain Orange Pi staged-route warning and eventual return plan.
- [x] Document credentials, labels, backend port, backup/rollback, and limits without disclosing secret values.
- [x] Re-run config validation, route smoke tests, whitespace checks, and manager task health before reporting completion.

### Task 5: Disable public self-registration

**Files:** Modify GitLab application setting through `gitlab-rails runner`; document in `docs/services/gitlab.md` and changelog.

- [x] Confirm the prechange Rails read returns `signup_enabled=true` (observed on 2026-09-15).
- [x] Apply `::Gitlab::CurrentSettings.update!(signup_enabled: false)` in the active GitLab container without changing users or app config files.
- [x] Re-read the setting and verify public `/users/sign_up` does not present a registration form; keep `/users/sign_in` 200.
