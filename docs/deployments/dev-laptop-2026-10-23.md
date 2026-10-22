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
  explicit user action. The Mac client is also updated to `0.81.3` and remains
  connected with its existing profile.

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

- The workspace transfer and remote audit are complete: the copy is `8.4G`,
  no excluded runtime directories or exact environment files were found, and
  Docker Engine `29.1.3` with Compose v2 is accessible by the operator.
- The SSH host-key change was verified against the laptop's own
  `/etc/ssh/ssh_host_ed25519_key.pub` (`SHA256:EA4G3ch9BWv/loC14ejsSDbshIRL6Wf3a5B9hAunlW8`)
  before updating the local `known_hosts` entry.
- The login-shell PATH was repaired so Node.js `24.0.2`, npm `11.3.0`, Bun
  `1.3.14`, Go `1.26.3`, Rust `1.99.1`, Codex `0.157.1`, Claude Code
  `2.1.308`, OpenCode `1.18.32`, and NetBird `0.81.3` resolve in fresh SSH
  sessions.
- Fingerprint enrollment is complete for `right-index-finger`, and the
  `fprintd` PAM profile is enabled while password authentication remains
  available as fallback.
- No NetBird setup key or other production credential is copied into this
  workstation document or transfer.
