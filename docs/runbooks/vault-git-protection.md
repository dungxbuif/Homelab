---
type: Runbook
title: "Vault Git protection"
description: "Local Git history and GitLab remotes for the Obsidian and Note vaults"
timestamp: 2026-10-14T00:00:00+07:00
---

# Vault Git protection

The vaults are now protected by local Git history before any remote sync:

| Vault | Local path | Branch | GitLab project |
| --- | --- | --- | --- |
| Obsidian Vault | `/Users/dungxbuif/workspace/Obsidian Vault` | `master` | `dungxbuif/obsidian-vault` |
| NoteVault | `/Users/dungxbuif/workspace/NoteVault` | `main` | `dungxbuif/note-vault` |

Obsidian workspace state, LiveSync data, local databases, caches, environment
files, credentials, and nested independent repositories are ignored. The
working snapshot is clean in both vaults and the initial local commits are:

- Obsidian Vault: `bd00a27 chore: snapshot current vault safely`
- NoteVault: `e25ffcd chore: initialize note vault history`

The remotes are configured with GitLab SSH URLs on port `2222`. The GitLab
account is the existing `dungxbuif` account and the projects are private.
Pushing is intentionally pending until an SSH key is authorized for that
account: the account currently reports zero SSH keys and the local 1Password
agent reports no identities. Do not replace this with a password or a token in
the repository.

## First push after SSH authorization

```bash
git -C '/Users/dungxbuif/workspace/Obsidian Vault' push -u origin master
git -C '/Users/dungxbuif/workspace/NoteVault' push -u origin main
git -C /Users/dungxbuif/workspace/homelab push gitlab HEAD:main
```

Before pushing, verify the remote with `git ls-remote` and confirm that the
1Password SSH agent exposes only the intended GitLab key. The homelab project
was created with a starter README, so reconcile that initial commit before the
first push; do not force-push over it without a reviewed merge.
