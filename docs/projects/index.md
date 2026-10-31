# Projects

One internal doc per project checkout, following the [project documentation standard](/docs/standards/project-documentation.md). New docs start from [the template](/docs/projects/_TEMPLATE.md).

## Deployed

- [CouchLoom](/docs/projects/couchloom.md) — `internal` · Private MCP server and local semantic index over the Obsidian CouchDB vault; Compose on VM100
- [db-management](/docs/projects/db-management.md) — `internal` · LAN-only database administration and backup verification hub (API, worker, web, CloudBeaver, Databasus); Swarm stack on VM110
- [Whiteboard (devtool)](/docs/projects/devtool.md) — `internal` · Self-hosted Excalidraw-style collaborative whiteboard (Go backend, React frontend, collab, MCP); Compose on VM100
- [homelab-ops](/docs/projects/homelab-ops.md) — `internal` · Central ops repository: Ansible, Swarm stacks, routes, backup contracts, automation image and CI for the lab
- [Homepage](/docs/projects/homepage.md) — `public` · Static nginx bookmark page for the self-hosted tools, served at dungxbuif.com from Swarm on VM100
- [K8s Syntax](/docs/projects/k8s-syntax.md) — `lab` · Static kubectl/YAML syntax drill app on nginx, k8s-syntax.dungxbuif.com on VM100 Swarm
- [Mac OCR (OCR Platform)](/docs/projects/mac-ocr.md) — `public` · API-first OCR/scan platform: Go proxy on VM100 Swarm at ocr.dungxbuif.com, Apple Vision workers in a native Mac app
- [MezonHook](/docs/projects/mezonhook.md) — `public` · Static Vite/React Mezon webhook message builder, public demo at mezonhook.dungxbuif.com on VM100 Swarm
- [My Family Tree](/docs/projects/my-family-tree.md) — `internal` · Self-hosted family genealogy app (Next.js on Bun) at family.dungxbuif.com, run from a bind-mounted source tree on VM100
- [MyPocket](/docs/projects/mypocket.md) — `public` · Personal finance Go API + worker for the native iOS app, API-only at money.dungxbuif.com on VM100
- [RelayHub](/docs/projects/relayhub.md) — `public` · Managed event, webhook, queue and realtime relay; Rust v1 Swarm stack on VM100 with the legacy Go Compose kept as rollback

## Not deployed

- [99Tech Code Challenge](/docs/projects/99tech-code-challenge.md) — `none` · Interview code-challenge solutions; not deployed
- [apps (stray folder)](/docs/projects/apps.md) — `none` · Loose folder holding a copy of the db-management web package; not a project of its own
- [Browser Bridge](/docs/projects/browserbridge.md) — `none` · Go server + Chrome MV3 extension that lets an agent drive the owner's Chrome; not deployed
- [Code Challenge](/docs/projects/code-challenge.md) — `none` · Second copy of the 99Tech code-challenge solutions; not deployed
- [Cortex](/docs/projects/cortex.md) — `none` · Personal AI system (Go modular monolith, OpenAI-compatible API for Open WebUI); not deployed
- [Datcom Clone](/docs/projects/datcom-clone.md) — `none` · NestJS Mezon bot (datcom-app); not deployed
- [Doino Bot](/docs/projects/doino.md) — `none` · Mezon bot for group food-order debt tracking (NestJS + TypeORM); not deployed
- [Donation Leaderboard](/docs/projects/donation.md) — `none` · Next.js donation leaderboard on Cloudflare Workers (OpenNext); not in the lab
- [Flotsam](/docs/projects/flotsam.md) — `none` · Spaced-repetition / Anki-compatible flashcard app (Bun monorepo); not deployed
- [Fox Spirit](/docs/projects/fox-spirit.md) — `none` · Telegram bot workspace data (GoClaw-era); not deployed
- [Go Study](/docs/projects/go-study.md) — `none` · Go learning wiki for Node.js developers; not deployed
- [Real-time Digital Auction Hub](/docs/projects/graphql-real-time-digital-auction-hub.md) — `none` · GraphQL federation study project; not deployed
- [Harness](/docs/projects/harness.md) — `none` · Markdown-first SDLC framework for AI coding agents; not deployed
- [Homelab Tunnel](/docs/projects/homelab-tunnel.md) — `none` · Design specs for an FRP-based service registration and tunnel system; no code, not deployed
- [Knowledgebase](/docs/projects/knowledgebase.md) — `none` · Personal technical notes (caching); not deployed
- [Learn](/docs/projects/learn.md) — `none` · Study notes and exercises (Go, Node.js, TOEIC); not deployed
- [llm-flashcard](/docs/projects/llm-flashcard.md) — `none` · Tauri desktop app turning study material into grounded flashcards; not deployed
- [Mezon Desktop](/docs/projects/mezon-desktop.md) — `none` · Native Rust/GPUI Mezon desktop client; not deployed
- [mezon-sdk-go](/docs/projects/mezon-sdk-go.md) — `none` · Go port of the Mezon TypeScript SDK (library); not deployed
- [MezonDong](/docs/projects/mezondong.md) — `none` · Pre-dev research and sketches for an MMN (Mezon Dong) explorer / Social-Fi; not deployed
- [My CV](/docs/projects/my-cv.md) — `none` · Next.js personal CV site; not deployed
- [n8n-nodes-mezon](/docs/projects/n8n-nodes-mezon.md) — `none` · n8n community nodes for Mezon; installed in the running n8n
- [NoteVault](/docs/projects/notevault.md) — `none` · Personal note repository; not deployed
- [PocketNode](/docs/projects/pocketnode.md) — `none` · Agent-harness experiment repo (README is the harness-experimental template); not deployed
- [Project Learn](/docs/projects/project-learn.md) — `none` · Reference checkouts of OSS projects for study; not deployed
- [QN Office](/docs/projects/qnoffice.md) — `none` · Quy Nhon office management portal + Mezon bot (Nx monorepo); not deployed in the lab
- [Random Template Code](/docs/projects/random-template-code.md) — `none` · Reusable helper snippets (Google, Outlook, mailbox, calendar sync); not deployed
- [Runtime Roasters](/docs/projects/runtimeroasters.md) — `none` · Go farm-to-cup coffee supply-chain platform (portfolio/course); not deployed
- [SpeedyDD](/docs/projects/speedydd.md) — `none` · Older API services + frontend (Node, AWS ECS / GCP); not deployed
- [Study](/docs/projects/study.md) — `none` · Empty directory
- [Test Clone](/docs/projects/test-clone.md) — `none` · Checkout of the upstream AI Website Cloner Template; not deployed
- [TOEIC](/docs/projects/toeic.md) — `none` · TOEIC study material processing workspace; not deployed

## Retired

- [BĐS Ngọc Tịnh](/docs/projects/bds-ngoctinh.md) — `none` · Next.js + Prisma real-estate CMS; retired from the lab
- [homelab-legacy](/docs/projects/homelab-legacy.md) — `none` · Retained snapshot of the old homelab source tree moved out of the vault on 2026-10-28; retiring
- [selfhost](/docs/projects/selfhost.md) — `none` · Older self-hosting manifests (Docker, Kubernetes v1, VPS v1); superseded by homelab-ops
