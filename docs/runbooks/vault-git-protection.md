---
type: Runbook
title: "Vault Git protection"
description: "Local Git history and GitLab remotes for the Obsidian and Note vaults"
timestamp: 2026-10-14T00:00:00+07:00
---

# Vault Git protection

## Fresh initialization requested 2026-10-14

The owner requested new Git histories, not an export of old commits. Preserve
each vault's existing `.git` outside the vault before initializing a new `main`
repository. Keep all working files in place. Ignore local state and credentials,
scan the exact staged snapshot before committing or pushing, and verify the
remote commit after upload. Old Obsidian history contains LiveSync configuration
and must never be pushed. The earlier first-push commands below are superseded.

SSH authentication is now verified as `dungxbuif` using the Mac vault Git sync
key. Use the existing VPS SSH endpoint on port 2222; the old LAN SSH override
points at the wrong host. Do not change production infrastructure in this step.

## Verified outcome

Both vaults now have fresh `main` histories, each containing one root commit.
The old `.git` directories are preserved outside the vaults under
`/Users/dungxbuif/.local/share/vault-git-history-20261014/`.
Do not upload this archive, which includes historical credentials.

| Vault | Local path | Branch | GitLab project |
| --- | --- | --- | --- |
| Obsidian Vault | `/Users/dungxbuif/workspace/Obsidian Vault` | `main` | `dungxbuif/obsidian-vault` |
| NoteVault | `/Users/dungxbuif/workspace/NoteVault` | `main` | `dungxbuif/note-vault` |

Obsidian workspace state, LiveSync data, local databases, caches, environment
files, credentials, and nested independent repositories are ignored. The
working snapshot is clean in both vaults and the initial local commits are:

- Obsidian Vault: `cf58b9c chore: initialize clean vault history`
- NoteVault: `2b87c13 chore: initialize clean vault history`

The remotes are configured with GitLab SSH URLs on port `2222`. The GitLab
account is the existing `dungxbuif` account and the projects are private.
Both fresh histories have been pushed successfully. The authentication-only key
`Mac vault Git sync` expires 2027-10-14. Per-repo `core.sshCommand` uses the VPS
`103.82.21.202`, strict host checking and the local `~/.ssh/id_ed25519` key,
bypassing the outdated global LAN SSH override. No private key is stored in Git.

Exact staged snapshots passed Gitleaks 8.24.2 before the initial commits.
On 2026-10-14 the owner explicitly authorized uploading the fifteen previously
quarantined files to the private self-hosted GitLab repository. Their unresolved
scanner findings are accepted by the owner, not classified as scanner-clean.
Device credentials, plugin state, caches and old history remain excluded.
No note content was deleted. Redacted findings are stored in the archive
directory as `obsidian-scan.json`. A passing scan is not a guarantee of finding
every possible secret. No scheduled auto-sync was configured by this step.

## Subsequent pushes

```bash
git -C '/Users/dungxbuif/workspace/Obsidian Vault' push -u origin main
git -C '/Users/dungxbuif/workspace/NoteVault' push -u origin main
```

Review and scan intended changes before committing. Verify the remote main SHA
with `git ls-remote origin refs/heads/main` against `git rev-parse HEAD`.
The homelab automation repository is separate and was not reset in this step.
Its GitLab starter README commit must be reconciled before upload, without
force-pushing. Public docs need no change: this is internal vault storage only.
