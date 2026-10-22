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

## Installed tools

- Git, build tools, Python 3, jq, ripgrep, fzf, tree, zsh, tmux, shellcheck,
  pipx and Python venv support
- Docker Engine with Compose v2
- VS Code `1.143.0` from the official Microsoft apt repository
- Google Antigravity IDE `2.5.5`, CLI `agy` `1.4.5`, and the
  `Google.google-antigravity` VS Code extension `1.9.0`
- Node.js `24.22.1` through nvm, npm `11.19.1`, and Bun `1.3.14`
- Go `1.22.2` and Rust `1.99.1` through rustup/apt
- Starship, Codex CLI `0.163.0`, Claude Code `2.1.308` and OpenCode `2.1.3`
- GitHub CLI `2.45.0` and standard CLI utilities
- RustDesk `1.5.0`, enabled as a system service for remote access
- NetBird client `0.81.3`, enrolled with the self-hosted management service

## Desktop cleanup

- Firefox was intentionally removed because this laptop is used for coding,
  light office work and basic media playback. The Firefox Snap, Ubuntu
  transitional package, wrapper binary and user profile/cache were removed.
- No other non-essential GUI applications were found during the audit; Snap
  runtime components and desktop security packages were retained.
- AppArmor and `snapd.apparmor` were re-enabled and verified active after the
  cleanup.

## Shell

- `/usr/bin/zsh` is the login shell for `dungxbuif`.
- Oh My Zsh is installed under `~/.oh-my-zsh` with `git`, `docker` and
  `docker-compose` plugins.
- The existing nvm, Bun, Cargo, Go, local-bin and Starship initialization is
  preserved in `~/.zshrc`.

## RustDesk

- The ThinkPad RustDesk ID is `201182481`.
- Both the user and system-service profiles use the self-hosted ID server
  `103.82.21.202:21116` and relay `103.82.21.202`.
- The gateway public key is configured locally; passwords and private client
  material are intentionally excluded from this document.
- `rustdesk.service` is active after restart. TCP `21115–21117` are reachable
  from the ThinkPad, while `21118–21119` remain blocked as designed.
- The remote session still needs one real end-to-end test from outside the LAN.

## Transfer rules

Workspace Git history and source files were copied to the laptop without
`--delete`; destination-only files were preserved. Runtime-heavy directories
such as `node_modules`, virtualenvs, build caches, database data and Docker
volumes were excluded. No credentials were committed or pushed. Because this
was a direct workspace copy, ignored local files may still exist on the laptop;
they must not be committed and should be removed when no longer needed.

## Verification

After bootstrap, verify tool versions, Docker access, SSH key authentication,
NetBird enrollment, fingerprint enrollment locally, and a sample build from
each active project before treating the workstation as ready.

## Current verification blockers

- The workspace transfer and remote audit are complete. After removing the
  large unused `litellm` and `open-design` source trees, the workspace is about
  `6.0G` on the ThinkPad and about `6.9G` on the Mac. Docker Engine `29.1.3`
  with Compose v2 is accessible by the operator.
- The SSH host-key change was verified against the laptop's own
  `/etc/ssh/ssh_host_ed25519_key.pub` (`SHA256:EA4G3ch9BWv/loC14ejsSDbshIRL6Wf3a5B9hAunlW8`)
  before updating the local `known_hosts` entry.
- The login-shell PATH resolves Node.js `24.22.1`, npm `11.19.1`, Bun
  `1.3.14`, Go `1.22.2`, Rust `1.99.1`, Codex `0.163.0`, Claude Code
  `2.1.308`, OpenCode `2.1.3`, Antigravity CLI `1.4.5`, and NetBird `0.81.3`
  in fresh SSH sessions.
- RustDesk `1.5.0` is installed and `rustdesk.service` is active. The
  Antigravity desktop binary has the required root-owned `4755` Chromium
  sandbox; it must be launched from a graphical desktop session with a valid
  `$DISPLAY`, not from a headless SSH shell.
- Fingerprint enrollment is complete for `right-index-finger`, and the
  `fprintd` PAM profile is enabled while password authentication remains
  available as fallback.
- The old local NetBird setup key was rejected as invalid. The daemon is
  healthy and the ThinkPad is now enrolled with a one-off replacement key.
  Management, signal and relay are connected; the assigned NetBird address is
  `100.69.32.183/16`. The setup key was passed through a mode-`600` temporary
  file and removed immediately after enrollment. No NetBird setup key or other
  production credential is copied into this workstation document or transfer.
