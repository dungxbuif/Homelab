---
type: Plan
title: RelayHub Product Docs and Developer Kit Implementation Plan
generated:
  by: "process:vault-import"
  at: "2026-10-31T16:00:00+07:00"
stale_after: "2026-12-30T16:00:00+07:00"
---

# RelayHub Product Docs and Developer Kit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make RelayHub's Docusaurus docs explain useful product outcomes and let developers/agents download a matching, buildable integration kit.

**Architecture:** Keep the existing Docusaurus site and packaging scripts. A versioned content/capability manifest drives the human guide, text exports and release-aware downloads; runnable examples are checked against actual contracts. Product consumers connect to a managed RelayHub instance without deploying its internal services.

**Tech Stack:** Existing locked Docusaurus/MDX, Node build scripts, Python archive/check tooling, OpenAPI/JSON Schema, TypeScript/Go examples and Playwright.

**Spec:** [Product docs design](../specs/2026-10-31-relayhub-product-docs-design.md). Proposed version policy is v1 primary with explicit preview/planned labels and a public `Legacy v2` section (`legacy-v2`), without server-language branding; review before implementation.

## Global Constraints

- Keep the existing English locale and committed Docusaurus dependency lock; this work does not require a framework upgrade.
- Product consumers do not need to self-host or maintain RelayHub's internal components. Do not invent public signup, commercial pricing or uptime guarantees.
- Planned features are excluded from install-ready skill instructions and runnable quickstarts.
- Canonical public narrative lives in `web/docs/docs` as Markdown/MDX. Public docs explain product behavior and integration contracts; backend technology, core-code maps and operator details remain internal, outside site/static/versioned-doc inputs.
- Apply the public/internal boundary to HTML, llms files, search/sitemap, skills, contracts and archives. Preserve required client SDK dependencies/licenses and accurate auth/protocol details; do not publish server provenance or deployment bundles.
- Source/build automation belongs in `/home/dungxbuif/workspace/projects/RelayHub`; these plans/evidence belong in the homelab vault.
- Source archives must contain lockfiles and required fixtures. Dependency downloads remain necessary unless an artifact is explicitly verified offline-ready.
- No live docs deployment or public package publication is implied by implementation of this plan.

## Review Focus

1. A first-time reader thinks they must operate NATS/Redis/PostgreSQL — D1/D4 must demonstrate a hosted-instance quickstart without those prerequisites.
2. A legacy HMAC example or planned room API is presented as released v1 behavior — D1/D2 must fail mismatched version/evidence checks.
3. LLM text loses code blocks, links or MDX-only explanations — D2 must preserve tested examples and reject missing text fallbacks.
4. A downloaded SDK works only inside the author's monorepo — D3 must build/test extracted archives in a clean path containing spaces.
5. Backend details leak through legacy/static pages, generated text or downloads — D1–D4 must enforce public-only inputs, metadata projection and final-output checks, while preserving client build inputs/licenses.

---

## File map and execution

Paths below are relative to the RelayHub repo. The main agent owns this plan's self-review. One subagent may implement a docs task at a time; parallel work on webhook/realtime is allowed with disjoint files and frozen contract inputs.

| Files | Responsibility |
|---|---|
| `web/docs/content-manifest.json`, `web/docs/capabilities.json` | Version, status, navigation/text sources and evidence catalog |
| `web/docs/docs/intro.md`, `product/{use-cases,managed-service}.md`, `user/{get-started,first-event}.md` | Product outcomes and first successful integration |
| `web/docs/docs/integrate/{node,go,browser,webhooks}.md`, `security/auth.md` | Integration and credential boundaries |
| `web/docs/docs/concepts/{overview,delivery}.md`, `api/v1.md`, `legacy/overview.md` | Product-level flows, public contracts and legacy integration |
| Vault `docs/services/relayhub-internals.md` | Internal architecture, component choices, core-code map and operator references; never a site/export input |
| `web/docs/scripts/{build-reference.mjs,build-reference.test.mjs}`, `backend/scripts/{build-llms.sh,check-docs.py}` | Canonical machine-readable exports and contract checks |
| `web/docs/static/skills/relayhub-integration/`, `backend/scripts/build-skill.sh`, `backend/scripts/test-developer-kit.py` | Versioned integration skill and reproducible downloads |
| `examples/remake/{node-quickstart,go-quickstart,browser-realtime}/` | Minimal executable examples, included only for verified capabilities |
| `web/docs/tests/product-docs.spec.ts`, `web/docs/playwright.config.ts`, `.github/workflows/ci.yml` | Navigation/use-case/download verification |

`content-manifest.json` fields: `schema_version:1`, `primary_version`, `versions[]:{id,status,pages[]:{id,source,public_url,text_path,capability_ids}}`, `aliases[]:{from,to}`. Only public pages are eligible. `capabilities.json` is an internal build input with the design's exact fields/status enum; project only product/version/status/public API/SDK compatibility/limitations into public output. Never import the full evidence catalog into browser bundles. `source_commit` and evidence paths verify implementation internally; they are not public server documentation. D1 can publish preview docs before the new forks ship, using only verified existing v1 examples; D3 includes a component only when its artifact is available.

### Task D1: Rewrite the product journey around real use cases

**Files:** Create manifest/catalog and narrative files in the map, including the internal vault document; modify `web/docs/{sidebars.js,docusaurus.config.js}`, existing `docs/developer/{quick-integrate,webhooks,realtime,queue,streaming,functions}.md`, `docs/developer/skills-tab.mdx`, `docs/api/{open-api-overview,signature-and-streaming}.md`. Archive only reviewed public integration content under `web/docs/versioned_docs/version-legacy-v2/` with matching `versioned_sidebars/version-legacy-v2-sidebars.json` and `versions.json`; move old operator material to internal documentation before removing it from public inputs, including `web/docs/static/deploy/`.

**Interfaces:** Produces the content/capability manifests above. Core public narrative: problem → what users can build → what RelayHub manages → what their app owns → verified flow → limitations → next action. Public links identify product releases and distributable client SDKs; server source links/provenance remain in the internal catalog and vault.

- [ ] Write catalog checks in `backend/scripts/check-docs.py`: every primary page has one version and valid capability IDs; each runnable example is `released` or tested `preview`, never `planned`; Legacy HMAC links cannot appear as v1 auth prerequisites. Reject fixtures that mark unimplemented rooms released, expose a backend component diagram or include an internal operator/source page in the public manifest. Permit documented client language/runtime/auth requirements.
- [ ] Run `python3 backend/scripts/check-docs.py --product-catalog`; expect FAIL for missing catalog/flag. Record the old doc routes before moving content.
- [ ] Write use cases for receiving a webhook in a local application, receiving queued work after an agent reconnects, reliable backend delivery and live UI updates. Add collaborative rooms only as planned until C3 evidence exists. Quickstart begins with a RelayHub URL/workspace/credential and one SDK/CLI. Explain actor/key boundaries, sync/async receipts, retries and limits using product concepts. Public diagrams show application/provider → RelayHub → recipient/agent; name no backend engine, framework, datastore or internal service. Preserve the verified core-code map and implementation/deployment diagrams in vault `docs/services/relayhub-internals.md`, outside the public build/export roots.
- [ ] Run catalog checks and `npm --prefix web/docs run build`; expect PASS with strict broken-link/anchor checks. Review the rendered product page and first-use flow for integration needs and product behavior. Preserve safe public legacy URLs through the alias map; retire old internal/deployment URLs with 404/410 or a reviewed safe product redirect. Do not leave their files publicly reachable behind hidden navigation.
- [ ] Commit owned docs/catalog files only: `git commit -m "docs: explain RelayHub use cases and managed integration"`.

### Task D2: Generate consistent text and API references

**Files:** Create `web/docs/scripts/{build-reference.mjs,build-reference.test.mjs}`; modify `web/docs/scripts/build-public-guide.mjs`, `backend/scripts/{build-llms.sh,check-docs.py}`, `web/docs/package.json`. Generated files: `web/docs/static/{llms.txt,llms-full.txt,public-guide.txt}`, `static/versions/<version>/` text/contracts and compatibility aliases. Keep existing canonical contracts until a validated replacement exists.

**Interfaces:** `buildReference({root,manifest,check}):Promise<{outputs:string[],version:string}>`; CLI `node web/docs/scripts/build-reference.mjs [--check]`. It reads the content manifest, not a second handwritten Markdown list. `--check` compares expected bytes without rewriting. The current root text files select `primary_version`; version-specific text stays available.

- [ ] Write `text_preserves_examples_and_version`: assert fenced example bytes and auth warnings survive generation; nested sidebar pages appear once; public URLs match configured base paths; an MDX widget without text fallback fails; an incorrect API version link fails. Assert an old `/docs/developer/auth.md` URL resolves safely without changing auth schemes. Inject internal source paths, component names and an internal-only API route into fixtures; assert they never appear in text/contracts or search/sitemap output, and generation fails on accidental inclusion.
- [ ] Run `node --test web/docs/scripts/build-reference.test.mjs`; expect FAIL for missing generator.
- [ ] Implement ordered Markdown/MDX extraction with parsed document structure, preserved code fences and deterministic public release metadata. Use existing Docusaurus dependencies where available; lock any added parser dependency. Build llms index/full text and text fallbacks from the public-only manifest; exclude internal catalog fields rather than redacting them after export. Make old shell entry points delegate to the new generator so CI callers remain valid. Separate v1/legacy public OpenAPI/message schemas and omit internal service endpoints. Validate contracts against route evidence internally or tag them incomplete; never finish the paused OpenAPI task implicitly as part of prose changes.
- [ ] Run generator tests, generator `--check`, existing `python3 backend/scripts/check-docs.py --static`, and strict Docusaurus build; expect PASS. Test both the standalone site and backend static-serving URL map in the existing `backend/scripts/test-docs-runtime.py` harness, without live credentials.
- [ ] Commit generated and source changes together: `git commit -m "docs: generate versioned agent references from canonical pages"`.

### Task D3: Package matching skills, SDKs and examples

**Files:** Modify `backend/scripts/build-skill.sh`, `web/docs/static/skills/relayhub-integration/{SKILL.md,references/authentication.md}`, versioned contract references, `web/docs/docs/developer/skills-tab.mdx`; create `backend/scripts/test-developer-kit.py`, `web/docs/downloads-manifest.schema.json`, `examples/remake/*` files listed in the map, and generated `web/docs/static/downloads/{manifest.json,relayhub-developer-kit-<version>.zip}` plus individual artifacts.

**Interfaces:** Preserve existing `build-skill.sh --check/--output`; add `--release-manifest PATH --kit-output DIR`. Consume C4 internal `release.json`, or a tested current-v1 manifest, only as verification input. Produce the design's allowlisted public projection: product release/status, public contracts and client SDK/CLI/skill version/runtime/download/SHA256/build/test fields. Do not copy server commits/upstream pins, images, private remotes, topology or full compatibility reports into public output. Do not label unavailable components as shipped. `test-developer-kit.py --artifacts DIR` verifies archives and runs declared clean builds.

- [ ] Write `test_kit_is_portable_and_versioned`: extract into a fresh temporary directory containing spaces, outside the repo; assert every relative dependency resolves, JS `npm ci && npm run build && npm pack` passes, Go `GOWORK=off go test ./...` passes, and examples use the manifest's contract version. Seed `.env`, server deployment/source files, private release metadata and cache fixtures and assert they never enter ZIPs/public manifests; tampered artifact fails SHA256 validation; two builds from identical inputs have identical bytes. Required client lockfiles/licenses must survive the public projection.
- [ ] Run `python3 backend/scripts/test-developer-kit.py --artifacts /tmp/relayhub-kit-fixture`; expect FAIL on the deliberately incomplete/mismatched fixture.
- [ ] Apply `skill-creator` and `superpowers:writing-skills` to update the focused integration skill and test its instructions against a disposable instance. The public skill covers delivery choice, auth, SDK usage and verification without teaching the backend stack or server setup. Planned APIs are reference-only, excluded from executable guidance. Extend the existing deterministic allowlisted ZIP builder with client SDK source/packages, required fixtures/licenses, examples and the public manifest; exclude server sources/images/config and operator procedures. Link CLI binaries only where verified. Keep real client package identities/dependencies/notices intact; remove monorepo-only `file:`/`replace` references or vendor the declared client dependency artifact. The outer manifest hashes the Kit; the Kit does not hash itself.
- [ ] Run artifact verifier, old `build-skill.sh --check`, fresh extraction builds and no-secrets/allowlist checks; expect PASS. Test the skill's documented quickstart against a disposable RelayHub URL using temporary credentials, and check logs/archives contain no credential values. Record tested platform/runtime versions and dependency network requirements.
- [ ] Commit source and intended generated assets only: `git commit -m "build: distribute versioned RelayHub developer kit"`. Do not publish to public registries or replace production downloads yet.

### Task D4: Verify the complete reader and agent journey

**Files:** Create `web/docs/tests/product-docs.spec.ts`, `web/docs/playwright.config.ts`; modify `web/docs/package.json`, `.github/workflows/ci.yml`, existing docs/runtime checks; add a source-owned release checklist `web/docs/RELEASE.md`. Create the vault evidence/runbook `docs/services/relayhub-product-docs.md` after verification.

**Interfaces:** CI command sequence: catalog/contract checks → reference generation/drift → strict site build → browser smoke → clean Kit tests. Docs release consumes the same component release manifest as code and refuses a mismatched compatibility report. Product docs remain independently buildable with preview labels while runtime plans are unfinished.

- [ ] Write `new_user_can_integrate_without_hosting_components`: in a real browser navigate Product → local webhook use case → quickstart → Node/Go guide → auth → downloads. Assert the journey explains RelayHub's managed service without backend stack details, badges/downloads/checksums agree and client source links match their released artifact. Fetch llms text and compare quickstart/limitations. Check final HTML/static/search/sitemap/versioned outputs and extracted skills/archives for internal technology/source/topology fixtures; only required client dependency metadata/licenses have a scoped exception. Direct requests to retired operator URLs must not return their old content. Test a safe legacy link and a planned capability warning.
- [ ] Run `npm --prefix web/docs run test:product-docs`; expect FAIL until the script/browser configuration is connected.
- [ ] Wire the tests into existing CI and add release gating, preserving current docs/contracts jobs. Provide a local preview and inspect desktop/mobile readability of the use-case navigation, code examples and download table. Internal deployment instructions use the existing docs serving path/ops workflow and exact artifacts. Publish a clean generated output and remove obsolete served assets/search entries/cache entries for retired internal pages; deploying new navigation alone is insufficient.
- [ ] Run the full CI command sequence and archived SDK builds; expect PASS with exact evidence. Review product claims against D1 catalog and actual webhook/realtime release reports. Update `released` only when a release exists; otherwise keep preview/planned. Document remaining unavailable downloads plainly.
- [ ] Commit/push feature branches for the parent repo and vault evidence: `git commit -m "test: verify product docs and developer kit journeys"`. Present the preview/build result for release review; no main merge is implied.

## Handoff and verification record

Planning only. Main-agent self-review maps product positioning to D1/D4, text/API consistency to D2, and skills/download portability to D3. The user already chose subagent execution; preserve that choice after review. Feature implementation and documentation can proceed in parallel, but documentation status promotion depends on actual feature/release evidence.
