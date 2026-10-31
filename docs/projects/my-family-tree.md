---
type: Project
title: My Family Tree
description: Self-hosted family genealogy app (Next.js on Bun) at family.dungxbuif.com, run from a bind-mounted source tree on VM100
generated:
  by: claude-code/opus-5.5
  at: "2026-10-31T18:00:00+07:00"
stale_after: "2027-01-29T18:00:00+07:00"
lifecycle: active
project: my_family_tree
class: internal
owner: dungxbuif
repo: dungxbuif/my-family-tree
deployed_revision: source copy matching 69fdf55 for app code (md5 compare 2026-10-31); .next built 2026-09-10
---

# My Family Tree

## Summary

Family genealogy app: tree and mindmap views, kinship-title finder, members
with avatars and galleries, Admin/Editor/Member roles, JSON/CSV/GEDCOM
import/export. Holds private family data. Class `internal` (exposed publicly
behind its own login, which by the gate table requires class `public`), owner
dungxbuif, status `active`.

## Source

| Field | Value |
|---|---|
| Local checkout | `/home/dungxbuif/workspace/projects/my_family_tree/` (branch `main`, HEAD `69fdf55`, 2026-09-22) |
| GitLab | `dungxbuif/my-family-tree` (default branch `main`) |
| Repo docs | `README.md` (Vietnamese), `DESIGN.md`, `docs/schema.sql`, `docs/migrations/` |
| Deployed revision | No git on the server. `/opt/apps/family-tree/src` matches `69fdf55` for `app/ components/ utils/ hooks/ context/ types/ scripts/ package.json bun.lock proxy.ts` |

## Internal architecture

- Next.js 16 (App Router) + React 19, run with `bun run start` (`next start`) on `:3000`.
- **How code reaches production:** there is no app image. The service runs the stock `oven/bun:1-slim` image and bind-mounts a copied source tree, `node_modules` and a prebuilt `.next` from `/opt/apps/family-tree/src` → `/app`. The tree was copied on 2026-09-10; `.next` (owned by root) was built then, so it was built inside a container on VM100. Updating the app means re-copying source and rebuilding `.next` on VM100 by hand.
- `/opt/apps/family-tree/run/` holds the earlier Compose file and a `.env` (2026-09-10) from before the Swarm service. Treat it as the likely source of the service env (unverified).
- Avatars/gallery: browser uploads directly to RustFS with presigned URLs; objects stay private and are served via `/api/storage/...`. README states bucket `mac-ocr`, prefix `family-tree` (live value unverified).
- The repo `Dockerfile` (multi-stage, non-root `nextjs`) is **not used** in production.

## Runtime

| Field | Value |
|---|---|
| Host / placement | VM100 (`node.hostname==vm100-prod`) |
| Stack / services | No stack. Standalone Swarm service `family-tree` 1/1 (created 2026-09-15, spec updated 2026-10-21) |
| Image | `oven/bun:1-slim` by **mutable tag**, no digest; args `bun run start`, workdir `/app`, runs as image default user (root, unverified) |
| Domain / exposure | `family.dungxbuif.com` · public → Pi5 Traefik router `family` → `tasks.family-tree:3000` |
| Networks | `edge-http-net`, `family-data-net` (PgBouncer is attached to `family-data-net`) |
| Mounts | bind `/opt/apps/family-tree/src` → `/app`; bind `/opt/apps/family-tree/uploads` → `/app/uploads` |
| Limits | 0.5 CPU / 512 MiB, no reservation |
| Update config | `stop-first`, `failure_action: rollback`, monitor 30s |
| Healthcheck | `bun -e fetch http://127.0.0.1:3000/login` every 30s, start period 15s |

## Data

| Store | Name | Backup class | Last restore evidence | RPO / RTO |
|---|---|---|---|---|
| PostgreSQL (`pgbouncer:6432`) | `family_tree` | in `backup/inventory.yaml`; not in the Databasus restore-verified set | none recorded | not stated |
| RustFS | prefix `family-tree` (bucket per README `mac-ocr`; inventory also lists bucket `family-tree`) | no scheduled RustFS backup | none | not stated |
| VM100 bind | `/opt/apps/family-tree/uploads` (4 KiB, effectively empty) and `src/` | none (no VM100 backup timers) | n/a | src is rebuildable from git |

## Secrets

Plain service env vars: `DATABASE_URL`, `S3_ACCESS_KEY_ID`,
`S3_SECRET_ACCESS_KEY`. Non-secret: `S3_ENDPOINT`, `S3_BUCKET`, `S3_PREFIX`,
`S3_REGION`, `UPLOAD_DIR`, `SITE_NAME`, `PORT`, `NODE_ENV`,
`FAMILY_TREE_IMAGE`, `FAMILY_TREE_PORT`. A copy lives in
`/opt/apps/family-tree/run/.env` (mode 600). 1Password paths: (unverified).

## Delivery

- CI: none (`.github/` exists but has no workflows).
- Staging: none. Prod: manual copy of source to VM100 + in-container `bun install` / `next build`, then `docker service update --force family-tree` (procedure reconstructed, unverified).
- Rollback: none recorded. There is no previous image; back up `src/` before replacing it.
- Catalog: `homelab-ops/automation/stacks/catalog.yml` id `family-tree`, `deployable: false`. Network repair script: `automation/scripts/repair-family-network.py`.

## Operations

- Health: `https://family.dungxbuif.com/login` (200, 2026-10-31).
- Logs: `docker service logs family-tree` (Pi5).
- Task cannot start after a node move → bind mounts exist only on VM100; placement must stay on `vm100-prod`.
- DB connection errors → check PgBouncer is still on `family-data-net` (repair script above).
- `oven/bun:1-slim` can change under the service on any re-pull.

## Gate status

| Gate | State | Evidence / exception (expiry) |
|---|---|---|
| G0 Intake | partial | GitLab repo, catalog entry; no `app.yml`; class/exposure mismatch |
| G1 Build | fail | No CI, no app image; code shipped as bind-mounted source |
| G2 Security | fail | Credentials in plain env vars; likely runs as root |
| G3 Runtime | fail | Hand-created service, mutable tag, host bind mounts, no stack |
| G4 Data | fail | No recorded restore of `family_tree` or its objects |
| G5 Observability | not assessed | |
| G6 Release | fail | No tags, no release notes, no rollback path |
| G7 Docs | partial | README deploy section is stale (Mac mini / Orange Pi topology); no `docs/configuration.md`, CHANGELOG |
| G8 Operate | not assessed | |

## Recent changes

- 2026-10-21: service spec updated (edge/network migration window; detail unverified).
- 2026-09-15: Swarm service `family-tree` created on VM100.
- 2026-09-10: source and `.next` build copied to `/opt/apps/family-tree/src`.
