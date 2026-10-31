---
type: Runbook
title: Vault Git protection
description: Local Git history and GitLab remotes for the Obsidian and Note vaults
generated:
  by: claude-code/opus-5.5
  at: "2026-10-31T00:00:00+07:00"
stale_after: "2027-01-29T00:00:00+07:00"
---

# Vault Git protection

Both Mac vaults have clean `main` histories pushed to private projects on the
self-hosted GitLab (`dungxbuif` account).

| Vault | Local path (Mac) | GitLab project |
| --- | --- | --- |
| Obsidian Vault | `/Users/dungxbuif/workspace/vaults/secondbrain` | `dungxbuif/obsidian-vault` |
| NoteVault | `/Users/dungxbuif/workspace/NoteVault` | `dungxbuif/note-vault` |

- Remotes use GitLab SSH on the VPS: `103.82.21.202:2222`. Per-repo
  `core.sshCommand` pins that host with strict host-key checking and
  `~/.ssh/id_ed25519`, bypassing the outdated global LAN SSH override.
- Auth key `Mac vault Git sync` expires **2027-10-14**.
- Ignored: Obsidian workspace state, LiveSync data, local databases, caches,
  env files, credentials, nested repos.
- The pre-reset `.git` directories are archived at
  `/Users/dungxbuif/.local/share/vault-git-history-20261014/` (with redacted
  scan output `obsidian-scan.json`). They contain historical credentials
  (including LiveSync config): **never push or upload them.**
- Fifteen files with unresolved scanner findings were pushed with explicit
  owner acceptance; they are accepted, not scanner-clean.
- No scheduled auto-sync is configured.

## Pushing changes

Review and scan (Gitleaks) the staged snapshot before committing, then:

```bash
git -C '/Users/dungxbuif/workspace/vaults/secondbrain' push origin main
git -C '/Users/dungxbuif/workspace/NoteVault' push origin main
git ls-remote origin refs/heads/main   # must equal: git rev-parse HEAD
```

Never force-push. The homelab automation repository is separate and is not
covered by this runbook.
