# Workspace replication: 2026-10-23

## Purpose

Create a working copy of the Mac development workspace on the ThinkPad at
`10.10.0.13` for local development and recovery.

## Source and destination

- Source: `/Users/dungxbuif/workspace/`
- Destination: `/home/dungxbuif/workspace/`
- Transport: `rsync` over SSH using the existing local SSH key
- Mode: incremental, without `--delete`; existing destination-only files are preserved

The copy preserved repository `.git` directories, branches, staged changes, and
uncommitted source changes. The `.git/HEAD` checksums for `cortex`, `goclaw`,
and `homelab` matched after transfer.

## Excluded data

The replication excludes dependency directories, build/test caches, local
runtime data, database directories, SQLite files, and `*.DS_Store`. It does not
copy Docker/PostgreSQL/RustFS runtime state.

## Credential policy

- Git operations use SSH keys; no GitHub/GitLab access token is stored in the workspace.
- `homelab/local_vars.json` remains local and ignored by Git.
- OAuth client-secret JSON files remain local-only and are covered by repository ignore rules.
- A credential that has been pasted into chat or committed in historical Git
  data must be rotated; renaming or moving it does not make the old value safe.

## Repository work completed in this pass

- `cortex`: commit `8594a79`, pushed branch `feat/ctx-708`; Python suite `93 OK`, Go unit packages pass.
- `goclaw`: commit `bb798f0d`, pushed branch `codex/mezon-channel`; `go test ./...` passes.
- `mezonhook`: commits `f652097` and `8615566`, pushed branch `codex/mvp-webhook-builder`; schema `17/17` and web `32/32` pass.

Repositories with dirty branches, missing dependencies, generated artifacts, or
failing tests remain uncommitted until reviewed individually.
