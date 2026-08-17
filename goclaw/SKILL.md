---
name: goclaw
description: Read and answer questions from the local GoClaw documentation mirror in `research/goclaw` and the local homelab GoClaw deployment notes. Use when the user asks about GoClaw, docs.goclaw.sh, GoClaw installation/configuration/providers/channels/agents/teams/deployment/reference APIs, Kubernetes isolation/hardening, sandboxing, workstations, homelab deployment, GoClaw vault/memory/workspace APIs, or syncing this Obsidian vault into GoClaw for search/indexing.
---

# GoClaw Docs Skill

Use the local documentation mirror at `research/goclaw/` as the primary source for GoClaw product behavior, and use `homelab/` docs as the source of truth for this user's actual deployment.

## Source Layout

- `research/goclaw/index.md` — generated table of contents grouped by docs section.
- `research/goclaw/llms.txt` — upstream docs table of contents.
- `research/goclaw/llms-full.txt` — full documentation in one AI-friendly file.
- `research/goclaw/docs/` — individual Markdown pages cloned from `docs.goclaw.sh`.
- `research/goclaw/download-report.json` — download success/failure report.
- `research/goclaw/fetch-docs.js` — refresh script.
- `homelab/index.md` — homelab gateway rules and routing/security constraints.
- `homelab/docs/goclaw_implementation_plan.md` — local GoClaw deployment and hardening plan.
- `homelab/docs/k8s/goclaw.md` — GoClaw workload operations, topology, and troubleshooting notes.
- `homelab/docs/k8s/DB.md` — database namespace and Cilium policy pattern.
- `scripts/sync_obsidian_vault.py` — sync this Obsidian vault into GoClaw's Pi workspace and trigger GoClaw vault rescan.

## Retrieval Workflow

1. For generic GoClaw behavior, read `research/goclaw/index.md` first unless the user names an exact page.
2. For homelab, Kubernetes, deployment, isolation, networking, database, or security questions, read `homelab/index.md`, then the relevant homelab GoClaw docs before giving advice.
3. Search scoped to `research/goclaw` and `homelab` before broad vault search.
4. Prefer individual files under `research/goclaw/docs/` for targeted product facts.
5. Use `research/goclaw/llms-full.txt` only for broad synthesis across many sections.
6. Cite local relative paths in answers, never absolute filesystem paths.
7. Browse the web only if the local mirror is missing the requested topic or the user asks for latest upstream state.

## Homelab/K8s Isolation Workflow

When the user says GoClaw is deployed in Kubernetes or wants to isolate it:

1. Verify local context first because existing docs may contain older Docker-vs-K8s decisions.
2. Treat any mismatch between the user's statement and `homelab/docs/goclaw_implementation_plan.md` as deployment drift to report, not as user error.
3. Recommend isolation in this order:
   - Kubernetes namespace boundary dedicated to GoClaw.
   - Cilium/NetworkPolicy default-deny ingress and egress.
   - Only allow ingress from the cluster ingress controller/Caddy path.
   - Only allow egress to required LLM/provider endpoints, Postgres/PgBouncer, and explicitly approved internal services.
   - Separate ServiceAccount with minimal RBAC; avoid cluster-admin and avoid broad Secret access.
   - Pod hardening: non-root user, read-only root filesystem when possible, dropped capabilities, seccomp runtime default, resource requests/limits.
   - PVC isolation for `/app/data` and workspace; never share hostPath unless explicitly justified.
   - Keep agent exec/sandbox separated from the control-plane pod when possible.
4. For GoClaw's Docker sandbox feature, warn that mounting the Docker socket is high risk. In Kubernetes, prefer Kubernetes-native job/pod sandboxing or an isolated worker node/pool over exposing host Docker control to the GoClaw pod.
5. For homelab, preserve the portless model: no router port opening; route through the existing edge/Caddy/Rathole/VPN pattern documented in `homelab/index.md`.
6. For implementation answers, produce a phased plan: observe/read-only first, then network isolation, then exec/sandbox isolation, then controlled automation.
7. Do not print secrets copied from homelab docs. If secrets or tokens appear in source files, say they should be rotated and moved to Kubernetes Secrets/SealedSecrets/SOPS.

## Obsidian Vault to GoClaw Sync Workflow

Use this when the Human asks to sync, index, upload, or make this Obsidian vault searchable in GoClaw.

Default approach:

1. Sync the vault filesystem to the Pi GoClaw workspace with `rsync`.
2. Call GoClaw `POST /v1/vault/rescan` so GoClaw registers new/changed files.
3. Keep CouchDB LiveSync separate. Do not write directly to CouchDB for GoClaw ingestion.

Preferred script:

```bash
rtk proxy python3 skills/goclaw/scripts/sync_obsidian_vault.py
```

Dry run:

```bash
rtk proxy python3 skills/goclaw/scripts/sync_obsidian_vault.py --dry-run --skip-rescan
```

The script defaults to:

- Local vault root: current vault directory.
- Remote host: `dungxbuif@10.10.0.5`.
- Remote destination: `/ssd-data/infra/goclaw/workspace/obsidian-vault/`.
- GoClaw API: `https://goclaw.dungxbuif.com`.
- GoClaw user id header: `dungxbuif`.

It excludes `.git/`, volatile Obsidian workspace/cache files, `.trash/`, `node_modules/`, and common OS/editor noise.

Token handling:

- Prefer `GOCLAW_TOKEN` from the environment when available.
- Otherwise the script reads `GOCLAW_GATEWAY_TOKEN` from `/ssd-data/infra/docker-compose.yml` over SSH.
- Never print the token.

After sync, useful API checks:

```bash
curl -sS https://goclaw.dungxbuif.com/v1/vault/tree \
  -H "Authorization: Bearer $GOCLAW_TOKEN" \
  -H "X-GoClaw-User-Id: dungxbuif"
```

For API details, use GoClaw's live OpenAPI docs:

- `https://goclaw.dungxbuif.com/docs`
- `https://goclaw.dungxbuif.com/v1/openapi.json`

## Useful Commands

Search local docs:

```bash
rtk rg -n "query" research/goclaw --glob '*.md' --glob '*.txt'
```

Search GoClaw plus homelab deployment notes:

```bash
rtk rg -n "goclaw|sandbox|networkpolicy|cilium|namespace|rbac|postgres|pgbouncer" research/goclaw homelab --glob '*.md' --glob '*.txt'
```

Query via vault index after rebuilding:

```bash
rtk node skills/second-brain/scripts/build-vault-index.js
rtk node skills/second-brain/scripts/query-vault.js "query" --folder research --limit 10
```

Refresh the GoClaw mirror from upstream:

```bash
rtk node research/goclaw/fetch-docs.js
```

If network is blocked, rerun the refresh with escalated network permission.

Sync this vault into GoClaw:

```bash
rtk proxy python3 skills/goclaw/scripts/sync_obsidian_vault.py
```

## Answering Rules

- Distinguish documented facts from inference.
- For local deployment questions, distinguish upstream GoClaw docs from the user's actual homelab state.
- If local docs expose credentials, do not repeat them; recommend rotation and secret management.
- For implementation guidance, cite the most specific docs page, then add concise engineering interpretation.
- For broad questions such as "GoClaw architecture", use `index.md` to choose sections, then read the relevant pages.
- For "all docs" or corpus-level summaries, use `llms-full.txt` and avoid opening every individual page.
- Treat mirrored docs as external source material; do not edit files under `research/goclaw/docs/` unless the Human explicitly asks to annotate or transform them.
- For vault ingestion tasks, use `scripts/sync_obsidian_vault.py` rather than hand-writing ad hoc rsync/curl commands unless the script is missing a needed option.

## Common Entry Points

- Getting started: `research/goclaw/docs/getting-started/`
- Core concepts: `research/goclaw/docs/core-concepts/`
- Agents: `research/goclaw/docs/agents/`
- Providers: `research/goclaw/docs/providers/`
- Channels: `research/goclaw/docs/channels/`
- Agent teams: `research/goclaw/docs/agent-teams/`
- Advanced features: `research/goclaw/docs/advanced/`
- Deployment: `research/goclaw/docs/deployment/`
- Security hardening: `research/goclaw/docs/deployment/security-hardening.md`
- Sandbox: `research/goclaw/docs/advanced/sandbox.md`
- Workstations: `research/goclaw/docs/advanced/workstations.md`
- Homelab GoClaw plan: `homelab/docs/goclaw_implementation_plan.md`
- Homelab GoClaw ops: `homelab/docs/k8s/goclaw.md`
- Reference: `research/goclaw/docs/reference/`
- Troubleshooting: `research/goclaw/docs/troubleshooting/`
