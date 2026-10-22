# Development Laptop Bootstrap

## Scope

The ThinkPad X1 Gen 8 at `10.10.0.13` is being prepared as a development
workstation. It is not a homelab production node and must not receive public
routes or database workloads.

## Baseline

- Ubuntu 24.04, `x86_64`
- 15 GiB RAM, 4 GiB swap, 233 GiB root disk
- Wi-Fi LAN address `10.10.0.13`
- Synaptics Prometheus fingerprint reader detected
- SSH key access enabled for the local operator account

## Installed or planned tools

- Git, build tools, Python 3, jq, ripgrep, fd, zsh, tmux and direnv
- Docker Engine with Compose v2
- Node.js 24.0.2 through nvm, Bun 1.3.14
- Go and Rust user-local toolchains
- Starship, Codex CLI, Claude Code and OpenCode
- NetBird client `0.81.3` installed on the ThinkPad; enrollment remains an
  explicit user action. The Mac client is still `0.78.2` until its macOS
  installer is authorized with an administrator password.

## Transfer rules

Workspace Git history and source files may be copied to the laptop. Secrets,
private tokens, `.env` files, database dumps, private keys and generated caches
must not be copied or committed automatically. Credentials are re-enrolled
locally through the existing secret manager or each tool's login flow.

## Verification

After bootstrap, verify tool versions, Docker access, SSH key authentication,
NetBird `NeedsLogin` state, fingerprint enrollment locally, and a sample build
from each active project before treating the workstation as ready.

## Current verification blockers

- The transfer process is no longer running, but the final remote audit has
  not completed because the SSH host key for `10.10.0.13` changed after the
  initial bootstrap. Confirm the new ED25519 fingerprint on the laptop before
  replacing the old entry in the operator's `known_hosts`.
- Until that confirmation, Docker access, workspace size, excluded runtime
  volumes, and excluded environment files remain unverified on the laptop.
- Fingerprint enrollment still requires a physical touch on the ThinkPad.
- No NetBird setup key or other production credential is copied into this
  workstation document or transfer.
