# RelayHub product docs — release evidence

This is the internal operator/release record for the public RelayHub product documentation. It is intentionally outside `RelayHub/web/docs`'s public input allowlist and must not be linked from the public site, skill or Developer Kit.

## Scope and boundary

Public material explains what users can build, the managed-service boundary, client-visible behavior, authentication, versioned contracts and client SDK usage. It does not publish server implementation choices, source topology, deployment files, private routes, credentials or operator recovery procedures.

Internal architecture context stays in [`relayhub-internals.md`](relayhub-internals.md). Keep that file and this evidence record in the Homelab vault only.

## Source evidence

- RelayHub worktree: `/home/dungxbuif/workspace/projects/RelayHub/.worktrees/relayhub-product-docs`
- Branch: `codex/relayhub-product-docs`
- D1: `3b7d816` — managed product journey and public catalog
- D2: `ead627c` — manifest-driven versioned references and public static cleanup
- D3: `a521fdd` — versioned skill, SDK archives, examples, kit and checksums
- D4: `3aa0e9f` — browser journey, CI gates, release checklist and retired-asset removal
- Review fixes: `dcbb222` — public contract boundary scan, safe generated output, versioned artifacts, corrected SDK example, CI build gate and legacy redirect

All four commits are local feature-branch commits. No main merge is implied by this record.

## Verification recorded on 2026-10-31

- `node --test web/docs/scripts/build-reference.test.mjs` — 7 passed, including stale-file, path-traversal, symlink and multiline-widget regressions.
- `npm --prefix web/docs run test:product-docs` — 1 browser journey passed.
- `npm --prefix web/docs run build` — strict Docusaurus build passed.
- `.venv-docs/bin/python backend/scripts/check-docs.py --static --self-test` — catalog, contracts, public asset/archive boundary scan, generated artifacts, route parity, Admin snapshot and negative controls passed.
- `python3 backend/scripts/test-developer-kit.py --artifacts web/docs/static/downloads` — kit extraction/build/checksum/reproducibility gate passed.
- `python3 /home/dungxbuif/.codex/skills/.system/skill-creator/scripts/quick_validate.py web/docs/static/skills/relayhub-integration` — skill valid.
- `go test ./...` in backend — passed.
- `go test ./...` in `sdks/go` — passed.
- TypeScript SDK `typecheck`, `test`, size check and `npm pack --dry-run` — passed; 16 SDK tests passed.
- Admin `typecheck`, Vitest and build — passed; 10 files / 19 tests passed.
- `go -C backend generate ./web` — generated embed matches the public site build.
- Public Skill and SDK downloads are now named with the `v1` contract version; `/sdk/relayhub-integration.zip` remains only as a redirect to the versioned Skill archive.

The browser run used a locally installed Playwright Chromium. CI installs Chromium explicitly before the same smoke test.

## Public outputs

- Canonical product pages are selected by `web/docs/content-manifest.json`.
- `v1` is `preview`; `legacy-v2` is `legacy`; `collaborative-rooms` remains `planned`.
- Text output: `/llms.txt`, `/llms-full.txt`, `/public-guide.txt`.
- Version output: `/versions/index.json`, `/versions/v1/`, `/versions/legacy-v2/`.
- Discovery output: `/search-index.json`, `/sitemap.xml`, `/aliases.json`.
- Download authority: `/downloads/manifest.json` plus the versioned Developer Kit and SDK archives.
- Every download component has a SHA256 in the public manifest; the kit does not hash itself.

## Release procedure

1. Update the private release/capability evidence first. Keep a capability `preview`, `planned` or `legacy` unless the implementation and public contract have been reviewed.
2. Run the commands in `RelayHub/web/docs/RELEASE.md` from the product worktree.
3. Inspect the generated page, static text, search index, sitemap, versioned output and extracted kit for private source/topology fixtures.
4. Confirm retired operator paths return no old content and generated backend embedding contains only the current public build.
5. Commit the feature branch. Push the branch for review; do not merge main or publish packages/deployments as part of this docs release task.

## Known status

This is a preview documentation/release surface. The kit is a portable client distribution; it does not provision or maintain any RelayHub service component. Planned capabilities must remain warnings in catalog/text output and must not appear as working examples in the skill or kit.
