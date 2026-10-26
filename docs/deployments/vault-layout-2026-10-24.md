# Vault layout standardization

## Canonical locations

- Homelab infrastructure repository: `/Users/dungxbuif/workspace/vaults/homelab`
- Second-brain Obsidian vault: `/Users/dungxbuif/workspace/vaults/secondbrain`
- ThinkPad mirror: `/home/dungxbuif/workspace/vaults/{homelab,secondbrain}`

The old `workspace/homelab` and `workspace/Obsidian Vault` paths are retired. The
ThinkPad mirror is synchronized directly into the canonical `vaults` directory;
no archive copy is retained there.

## Git/worktree policy

The Homelab repository remains the direct checkout at `vaults/homelab`. Temporary
worktrees are not synchronized to the ThinkPad. Clean worktrees can be released
after their branch tips are preserved; dirty worktrees remain until their local
changes are reviewed. Historical documents under `docs/archived/` may retain old
paths as historical evidence, but active docs and scripts must use the canonical
paths above.

## Verification

- Both vaults contain `.obsidian` and remain valid Git checkouts.
- The ThinkPad mirror is checked with `rsync --dry-run` before destructive cleanup.
- Old ThinkPad paths are absent after the direct sync.
