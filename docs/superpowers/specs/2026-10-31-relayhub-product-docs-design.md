# RelayHub product documentation and Developer Kit

Date: 2026-10-31. Status: proposed design for review; no site, skill or package has been changed or published.

## Intent

The user explicitly chose Docusaurus and asked for product introduction, useful use cases, integration guides, core-code explanations, APIs, authentication and high-level design. They emphasized that the old docs do not explain clearly enough what users can build, and that users should not have to self-host or maintain RelayHub's internal components. They also requested `llms.txt`/full text, ready-to-install skills and SDK downloads that can be built together.

The product promise is managed integration: a consumer connects their application or outbound agent to a RelayHub instance, while the RelayHub operator maintains the servers, messaging and storage. This does not assert a public commercial offering, pricing, uptime guarantee or unrestricted signup exists. V1 accounts/workspaces remain admin-created according to the approved product design. Self-hosting instructions serve operators and are not prerequisites in the application integration journey.

## Current evidence

The source already contains `web/docs/docusaurus.config.js`, `sidebars.js`, `docs/`, `static/llms.txt`, generated `static/llms-full.txt`, and integration skill/SDK ZIPs. `web/docs/scripts/build-public-guide.mjs` gathers tutorial pages and invokes `backend/scripts/build-skill.sh` and `build-llms.sh`. Those scripts build deterministic archives/text, but public static Markdown duplicates some tutorial content and describes Go/v2 behavior. The skill includes an OpenAPI snapshot; it must not silently become an unverified Rust v1 contract.

The site currently uses English and Docusaurus 3.x from its committed lockfile. Keep both unless the user asks otherwise. This work does not require upgrading the docs framework. Centrifugo/room/Yjs capabilities are proposed in the [realtime design](2026-10-31-relayhub-centrifugo-fork-design.md), not implemented merely because upstream repos were cloned. The original [Rust v1 design](2026-10-29-relayhub-rust-v1-design.md) remains the source for durable/webhook behavior.

## Approaches and proposed choice

1. Rewrite prose within the current duplicated tutorial/static layout. Smallest edit, but the website, llms files and skill can keep contradicting one another.
2. Keep Docusaurus, use one canonical content manifest per product version, and generate text/download references from it. Add a release-aware Developer Kit using the existing deterministic packer. Recommended: existing tooling is reusable and compatibility becomes inspectable.
3. Regenerate the whole site/SDK surface from OpenAPI. Useful for reference tables, insufficient for product use cases, architecture or WebSocket behavior; also depends on unfinished Rust route parity.

Docusaurus is the user's explicit choice. Option 2 is the assistant's proposed implementation approach. Default version policy for review: v1 is the primary product narrative, with explicit preview/planned labels, and Go/v2 lives in a clearly marked Legacy section. No published contract is silently replaced by changing a navigation label.

## Reader journey and information architecture

| Section | Reader question and required content |
|---|---|
| Product | What is RelayHub, who uses it, what does the operator manage, and what still runs in my app? |
| Use cases | Receive provider webhooks locally; receive while an agent is offline; deliver backend work; show live progress; collaborate in a room when that release supports it |
| Start | Obtain an admin-provisioned workspace/app credential; install one SDK or CLI; connect outbound; send one event; inspect the result |
| Integrate | Separate Node, Go and browser paths; webhook sync/async, offline policy, retries, delivery status, replay and dashboard tests |
| Auth and tenancy | User session vs application key vs agent key vs short-lived browser token; permissions, revocation, endpoint auth, CSRF and safe credential placement |
| API and protocol | Versioned HTTP reference, WebSocket frames, errors, limits, receipt/ACK meaning, idempotency and runnable examples |
| How it works | High-level architecture and request flows; ownership boundaries, durable vs ephemeral state, failures/recovery; core modules and source links at the release commit |
| SDKs and agents | Supported versions, install/build commands, separate downloads, Developer Kit, skill usage and checksums |
| Operate | Optional deployment and operational responsibilities for the RelayHub operator; generic examples without homelab secrets or topology |
| Legacy and changes | Old Go/v2 contracts, migration notes and release compatibility; avoid mixing old signing examples into v1 quickstarts |

Every use case follows: the user's problem → what they can build → what RelayHub manages → what they implement → short working flow → relevant limitations → one next-step link. Lead with outcomes, not NATS/Redis/Centrifugo deployment instructions. Illustrate webhook delivery to a local app with an outbound agent, not a promise of arbitrary TCP/full-network tunneling. Clearly distinguish realtime's ephemeral behavior from durable queued delivery.

Each capability record contains `id`, `product_version`, `status` (`released`, `preview`, `planned`, `legacy`), `source_commit`, `evidence_paths`, `api_contract`, `sdk_versions` and `limitations`. A completed implementation test is evidence of preview readiness; a recorded release is required for `released`. Planned features are excluded from install-ready skill instructions and runnable quickstarts. API reference generation may consume validated contracts; docs must not invent a route to fill a gap.

## One source, multiple reading formats

Canonical narrative lives in `web/docs/docs` as Markdown/MDX; a checked manifest determines version, ordering, public URL, text export and capability references. Preserve code fences and exact commands. Dynamic widgets require a text fallback; generation fails rather than leaving JSX/imports in `llms-full.txt`. Current URLs and `/docs/*.md` aliases receive an explicit redirect/compatibility map instead of disappearing accidentally.

Generate `/llms.txt` as a short version/status index and `/llms-full.txt` as the current primary guide. Also expose version-specific text so legacy instructions cannot be mistaken for v1. Include source URLs and release/commit metadata in the full file. These are useful machine-readable resources; they do not guarantee any agent will discover or obey them. OpenAPI and message schemas remain separate linked artifacts, with the same version identity.

## Skills, SDKs and Developer Kit

Keep a focused `relayhub-integration` skill with an installable directory, versioned API/auth references and a verified end-to-end example. It teaches an agent how to choose a delivery mode, obtain credentials from the caller's secret store, integrate an SDK and verify a flow. It must not configure a user's production infrastructure or send live webhooks without that user's authorization. Use `skill-creator` and `superpowers:writing-skills` when implementing/revising the skill.

Keep individual Node/browser/Go source archives and JS package tarballs when built and tested. Go is a source/module distribution; do not invent a compiled universal Go SDK binary. Add a Developer Kit archive containing the compatible skill, available SDK artifacts, example projects, contracts, manifest and build instructions. CLI binaries can be linked if the release actually produces them; absent platform builds are marked unavailable, not fabricated.

Manifest fields: `schema_version`, `product_version`, `status`, `source_commit`, `contracts`, `components[]` with name/version/source commit/upstream base where applicable/runtime floors/relative URL/SHA256/build and test commands, and a compatibility-report reference. Build the bundle from declared, verified artifacts, not from a recursive zip of the working directory. Include licenses; exclude real credentials, `.env`, caches, ignored local worktrees, `.git` and `node_modules`. Do not include a hash of an archive inside itself; the outer download manifest contains that archive's hash.

Building the Kit requires normal language dependency retrieval unless explicitly labeled offline-ready; source archives must contain lockfiles and required fixtures. Fresh extraction into a path containing spaces, outside the monorepo, must build and test without parent `go.work`, local `file:` dependencies or missing fork checkouts. Built fork packages may be vendored as declared artifacts; source-only SDKs must identify reachable pinned dependencies.

## Acceptance and boundaries

- A new reader can choose a use case and complete one verified SDK/CLI flow without installing PostgreSQL, Redis, NATS or Centrifugo themselves.
- Site, text, skill and downloads identify the same API/release; planned features never appear as working production examples.
- Auth examples distinguish browser and backend secrets, with no operator-private values or addresses.
- Docusaurus strict-link build, machine-readable drift checks, contract/example checks, archive checksum/reproducibility tests and clean-extraction SDK tests pass.
- Public docs explain the core architecture; detailed homelab operations remain in the vault. No live docs deployment or package publication is performed by this design.

## Implementation sequence

See the [product docs plan](../plans/2026-10-31-relayhub-product-docs.md): D1 product/use-case rewrite and capability catalog; D2 shared text/contracts export; D3 skills/SDK Developer Kit; D4 cross-surface verification and release integration. The webhook plan supplies the exact webhook capability/evidence mapping; the realtime release manifest supplies fork compatibility. Independent prose work can start after review, but no feature is promoted to released before its own evidence exists.

## Design review evidence

A separate Luna builder review read this design on 2026-10-31 and returned `nothing important left`. The main agent separately reviewed the implementation plan. This is review of design/planning, not evidence that the website or Developer Kit has been implemented or tested. The v1-primary/Legacy default remains a proposal until the user reviews it.
