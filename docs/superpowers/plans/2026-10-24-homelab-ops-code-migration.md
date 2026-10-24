# Homelab Operations Code Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move all homelab code into homelab-ops with working consumers and complete reciprocal documentation.

**Architecture:** Homelab retains the knowledge vault and dated evidence; homelab-ops becomes the authoritative code/deployment repository. Use a manifest-driven, copy-verify-cutover-remove migration that preserves dirty edits and historical provenance.

**Tech Stack:** Existing Ansible, OpenTofu, shell/Python/Ruby tooling, Docker Swarm, GitLab CI; preserve supported existing runtimes.

**Spec:** `../specs/2026-10-24-db-management-design.md`

## Global Constraints

- H = `/home/dungxbuif/workspace/vaults/homelab`; O = `/home/dungxbuif/workspace/homelab-ops`.
- Preserve pre-existing dirty changes in both repos. No broad staging, reset or automatic stash.
- Do not commit `local_vars.json`, `credentials/`, private artifacts, state or caches.
- Retired Kubernetes/ArgoCD resources remain historical, never active inventory.
- Source removal requires verified destination contents and consumer cutover; no recursive directory deletion.
- Documentation states proposed versus verified deployment truthfully.

## Review Focus

- Dirty/untracked source omitted or destination collision overwritten: Task 1 manifests reject this.
- CI includes, forced-command paths or Semaphore clones still reference old roots: Tasks 2/3 enumerate consumers.
- Moved symlinks or executable permissions silently change behavior: Task 2 parity check.
- Private credentials/state enter the migrated repository: Tasks 1/2 exclusion and secret-scan gates.
- Vault links resolve locally but fail on GitLab: Task 4 checks relative and cross-repo links separately.

## File map and layout

Preserve relative paths of tightly coupled active trees initially:
`O/automation/`, `O/backup/`, `O/migration/` (only active deployment assets).
Use `O/archive/legacy-homelab/` for retired `iac/`, `deprecated/`, `kubernetes/`
and classified retired files; `O/archive/legacy-ops/` for existing historical
`k8s/` and `argocd-apps/`. Do not classify by directory name alone: active code
inside any tree goes to its operational location in the manifest.
Inventory `monitoring/`, `edge-registrar/`, `goclaw/`, `relayhub/` as well; active
embedded tools go under `O/tools/<name>/`, obsolete embedded application copies
under `O/archive/app-snapshots/<name>/` with upstream/commit provenance.

Create `O/docs/migrations/2026-10-24-code-map.json`,
`O/docs/migrations/2026-10-24-consumers.md`, `O/scripts/check-code-migration.py`,
`O/tests/test_code_migration.py`, `O/docs/OPERATIONS.md`, `O/docs/INDEX.md`,
`O/llms.txt`; update `O/README.md`, `.gitignore`, `.gitlab-ci.yml`.
Update H `README.md`, `index.md`, `llms.txt`, `docs/INDEX.md`, `docs/PROJECTS.md`,
`docs/CONTEXT.md`, `docs/STACK.md`, `docs/STATUS.md`, runbooks and local references
identified by the map. Add H `docs/deployments/2026-10-24-code-migration.md`.

### Task 1: Inventory and lossless mapping

**Files:** code-map.json, consumers.md, check-code-migration.py, test_code_migration.py.
**Interfaces:** Manifest entries `{source, destination, sha256, mode, type, lifecycle, owner, sourceCommit, dirty}`; excluded private paths record category only, never contents. `audit(sourceRoot, targetRoot, manifest) -> findings[]` is read-only.

- [ ] Record Git HEAD/status and baseline test commands for both repos. Enumerate tracked, untracked and ignored files; inspect ignored paths only by safe metadata until classification.
- [ ] Write tests `test_dirty_file_preserved`, `test_collision_rejected`, `test_private_path_excluded`, `test_unmapped_code_rejected`; assert no accepted manifest loses bytes or includes a credential/state file.
- [ ] Run `python3 -m unittest discover -s tests -p test_code_migration.py` in O. Expected: new audit behavior fails before implementation.
- [ ] Implement the audit and full file mapping; explicit lifecycle/ownership for every code asset. Record symlink targets without following them outside source roots.
- [ ] Run the same tests. Expected: PASS. Run `python3 scripts/check-code-migration.py inventory --source ../vaults/homelab --manifest docs/migrations/2026-10-24-code-map.json`. Expected: zero unmapped code/collisions/private payloads; destination parity is not yet required.
- [ ] Commit only the migration tooling/manifest/docs after reviewing the staged diff.

### Task 2: Copy code and make ops validation runnable

**Files:** mapped O destinations, `.gitlab-ci.yml`, `.gitignore`, code-local docs.
**Interfaces:** Consumes Task 1 map; produces content-identical destination copies plus documented path-only edits. Archive discovery is excluded from live inventory and deployment.

- [ ] Add `test_symlink_escape_rejected`, `test_executable_mode_preserved`, `test_hash_mismatch_rejected`; run Task 1 test command and observe the expected missing-check failures.
- [ ] Implement parity checks and stage mapped copies without deleting H files. Preserve user edits; record any destination preimage/collision resolution in the private migration evidence.
- [ ] Update tests, build contexts, script-relative paths, config roots and CI rules in O. Resolve private files through explicit operator-managed paths; do not silently source secrets from the old repository.
- [ ] Run `python3 scripts/check-code-migration.py verify --source ../vaults/homelab --manifest docs/migrations/2026-10-24-code-map.json`. Expected: copied hashes/modes/targets match, with individually recorded reviewed path edits.
- [ ] Run migrated CI validation commands from O `.gitlab-ci.yml`, including Python/shell/Ruby tests, ShellCheck, Ansible lint/syntax, OpenTofu fmt/validate and secret scan. Expected: baseline failures identified separately; no migration regression. No Terraform apply.
- [ ] Commit reviewed destination code, CI and evidence; retain H source until Task 3 acceptance.

### Task 3: Cut over actual consumers

**Files:** consumers.md, O automation/deployment configuration, H deployment evidence.
**Interfaces:** Consumer rows `{id, oldRef, newRef, verification, rollbackRef, status}`; no credential values.

- [ ] Inventory GitLab includes/variables, runners, registry paths, Semaphore repositories/templates, forced commands, cron/systemd working directories, helper paths and documentation code references. Mark unreachable consumers as unverified.
- [ ] Validate new CI config through GitLab CI lint and run read-only audit jobs using O. Expected: correct repo/ref, valid config, audit outputs equivalent to pre-cutover observations.
- [ ] Change one enrolled consumer at a time to a pinned O commit; retain its old repository/ref and configuration for rollback. Schedule owners remain unchanged by a source move.
- [ ] Run the consumer's existing smoke/no-op check after each cutover. Expected: success from O with no unintended deployment, missing file or secret exposure. Stop that consumer on failure and restore its saved reference.
- [ ] Record each result and commit consumer definitions. If credential/access is unavailable, leave source copies and explicit pending rows; do not claim migration complete.

### Task 4: Remove verified source copies and reconcile navigation

**Files:** mapped H code paths, both repo READMEs/indexes/llms, H affected docs, O operations docs.
**Interfaces:** Consumes successful consumer rows and parity manifest; produces H vault without executable source and O canonical ownership index.

- [ ] Generate the exact source-removal list from accepted mapping rows; re-hash sources against recorded copies so edits made during migration prevent removal.
- [ ] Remove only listed code files after destination commits and consumer acceptance. Retain historical prose with a migration note; move code-local README with the code. Never bulk-delete roots or credential directories.
- [ ] Update all active command paths and links. Use relative links within a repo and canonical GitLab blob/tree links across repos; document both current Linux checkout locations and optional sibling-checkout conventions.
- [ ] Add O contributor/deploy/rollback/test instructions and H navigation/ownership summary with reciprocal links. Record retained secret locations privately and how ops references them.
- [ ] Run migration audit in `final` mode, link validation and both repo secret scans. Expected: zero unmapped code, broken active local links, missing destination files or references to removed executable paths; historical references carry explicit provenance.
- [ ] Review diffs in both repos and commit only scoped changes. Record exact source/destination commits and any pending live consumer in the migration report.

## Completion

Do not start application production deployment through O until its operational
workflow is validated. Local app implementation may proceed while remote access
is blocked. Migration completion requires source parity, live consumer cutover,
documentation coverage and recoverable destination commits, not just copied files.
