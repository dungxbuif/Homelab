# Vault source retrieval verification

Read-only verification on 2026-10-15. Both GitLab projects are private, their
`main` branches are protected, and the original local working trees are clean.
API branch IDs match local HEAD. Independent fresh clones were then fetched
over the GitLab SSH endpoint through the VPS, without sharing or printing tokens.

| Project | Local source | Verified commit | Tracked entries |
| --- | --- | --- | --- |
| `dungxbuif/obsidian-vault` (3) | `/Users/dungxbuif/workspace/vaults/secondbrain` | `3a71cabc3fdb93eef67a0f72ba1fb9095cdd873c` | 1954 |
| `dungxbuif/note-vault` (4) | `/Users/dungxbuif/workspace/NoteVault` | `2b87c13dda45d0981d57e1ac93ab73f5f9185a32` | 6 |

Fresh-clone `git fsck --full --strict` returned exit 0 for both repositories.
Their HEADs match the originals; tree IDs are respectively
`44bdf15bd4429703d0b957a4136784dd9796791d` and
`8bbde1215615144ac4e0b3e0c244fa82d8a7ac76`. Neither tree contains gitlinks or
Git LFS pointer markers. Clones were made without checkout, so no vault plugins,
hooks from source, application code or install scripts were executed. Temporary
verification clones are disposable; no original repository was modified.

## Coverage limits

This proves current tracked Git source is retrievable from GitLab, not that
Google Drive contains a restorable GitLab backup or that ignored files are saved.
It is not continuous synchronization and does not certify future edits.

- Obsidian excludes device/workspace state, plugin credential files, Copilot
  caches, generated indexes, dependency trees, trash, local environment files
  and LocalStack cache/certificate artifacts. No ignored content was force-added.
- `projects/blockchain-mainnet-explorer/mmn-tx-explorer` is an explicitly ignored
  independent repository, clean at `d92607fbb93d0b9e5baa70199b38f78e747d4cf9`.
  Its separate remote/recovery is not verified by this vault clone.
- `studying/message-queue/code` contains only an empty `.git` directory, with
  zero objects and no working files at observation. It is not a saved code project.
- NoteVault contains the starter note and Obsidian configuration; six tracked
  entries must not be presented as a populated copy of all study materials.
- Homelab automation is a separate project and branch. Unreconciled dirty or
  untracked files in its original workspace are not covered by this verification.

Use GitLab source history to recover tracked notes and source. Use the separate
native GitLab backup/restore workflow for instance disaster recovery, including
repositories, database, configuration and object-storage dependencies. A successful
clone does not replace that restore rehearsal. No public app docs change.
