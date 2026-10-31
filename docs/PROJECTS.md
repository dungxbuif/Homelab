---
type: Reference
title: "Local Project Workspace Inventory"
description: "Summary-only project inventory for source checkouts kept outside the Homelab repo"
timestamp: 2026-10-31T10:30:00+07:00
---

# Local Project Workspace Inventory

Homelab keeps only the project inventory, notes, local folder paths, and remote
origin links. Project source checkouts live directly under:

```text
/home/dungxbuif/workspace/projects/
```

Do not commit independent application source trees into the Homelab
infrastructure repository. Use this file as the map from Homelab documentation
to the source checkouts.

## Layout Policy

- Keep Homelab operations, diagnostics, and infrastructure docs in this repo.
- Keep independent project source repositories under `/home/dungxbuif/workspace/projects/<project>/`.
- Keep remote origin links here when available.
- Leave projects with no recorded `origin` as local-only until a remote is added.
- `MyPocket` is included in this inventory at
  `/home/dungxbuif/workspace/projects/MyPocket/`.

## Project and reference flow

![Project management and reference-note flow](./assets/diagrams/project-reference-flow.svg)

The project checkout remains the implementation source. This inventory records
where it lives and which remote it uses; dated deployment records capture what
actually reached runtime; `STATUS.md`, `STACK.md` and `BACKLOG.md` summarize the
current operational decision. Do not mark a project or rollout complete from a
source change alone without runtime or restore evidence where applicable.

## Remote publication audit

As of 2026-10-31, the workspace contains 35 Git repositories and 11 non-Git
directories. Four Git repositories already use a GitLab remote
(`NoteVault`, `db-management`, `homelab-ops` and `homepage`); the other 31 Git
repositories do not yet have a GitLab remote, including `Flotsam` and `learn`
which have no remote at all. The requested GitLab mirror wave is not applied
yet. Before creating projects or pushing source, classify the 11 non-Git
directories and choose the GitLab visibility/namespace; keep the token outside
the repository and record only the resulting project URL and verification. A
2026-10-31 preflight found the local token file with mode `0600`, but the
public GitLab API returned `HTTP 500` for authenticated requests. A Rails log
trace identified the root cause as Redis DNS failure after the Redis container
lost its `gitlab-net` attachment; the overlay attachment and persistent
override were repaired. GitLab now resolves `redis-prod`, authenticated Redis
DB2 returns `PONG`, and unauthenticated API calls return the expected `401`.
Project creation and remote pushes remain blocked until the PAT used in that
preflight is revoked/rotated because it was exposed in a shell error. See
[the repair evidence](./deployments/gitlab-redis-network-repair-2026-10-31.md).

## Project Inventory

| Project | Local folder | Remote origin | Notes |
| --- | --- | --- | --- |
| `99tech_code-challenge` | `/home/dungxbuif/workspace/projects/99tech_code-challenge/` | `git@github.com:harrybui-dev/99tech_code-challenge.git` | Git checkout |
| `apps` | `/home/dungxbuif/workspace/projects/apps/` | none | Local grouping directory; not a standalone Git project |
| `BrowserBridge` | `/home/dungxbuif/workspace/projects/BrowserBridge/` | `git@github.com:dungxbuif/browserbridge.git` | Git checkout |
| `Flotsam` | `/home/dungxbuif/workspace/projects/Flotsam/` | none recorded | Git checkout without origin |
| `GraphQL_Real-time-Digital-Auction-Hub` | `/home/dungxbuif/workspace/projects/GraphQL_Real-time-Digital-Auction-Hub/` | `git@github.com:dungxbuif/GraphQL_Real-time-Digital-Auction-Hub.git` | Git checkout |
| `Knowledgebase` | `/home/dungxbuif/workspace/projects/Knowledgebase/` | `git@github.com:dungxbuif/Knowledgebase.git` | Git checkout |
| `MezonDong` | `/home/dungxbuif/workspace/projects/MezonDong/` | none recorded | Local directory |
| `MyPocket` | `/home/dungxbuif/workspace/projects/MyPocket/` | `git@github.com:dungxbuif/MyPocket.git` | Git checkout; production app source |
| `NoteVault` | `/home/dungxbuif/workspace/projects/NoteVault/` | none recorded | Local directory |
| `PocketNode` | `/home/dungxbuif/workspace/projects/PocketNode/` | `git@github.com:dungxbuif/PocketNode.git` | Git checkout |
| `QnOffice` | `/home/dungxbuif/workspace/projects/QnOffice/` | `git@github.com:tiennguyenvan-ncc/QnOffice.git` | Git checkout |
| `RelayHub` | `/home/dungxbuif/workspace/projects/RelayHub/` | `git@github.com:dungxbuif/RelayHub.git` | Git checkout; production app source |
| `RuntimeRoasters` | `/home/dungxbuif/workspace/projects/RuntimeRoasters/` | `git@github.com:dungxbuif/RuntimeRoasters.git` | Git checkout |
| `bds-ngoctinh` | `/home/dungxbuif/workspace/projects/bds-ngoctinh/` | `git@github.com:dungxbuif/bds-ngoctinh.git` | Git checkout |
| `code-challenge` | `/home/dungxbuif/workspace/projects/code-challenge/` | `git@github.com:dungxbuif/code-challenge.git` | Git checkout |
| `cortex` | `/home/dungxbuif/workspace/projects/cortex/` | `git@github.com:dungxbuif/cortex.git` | Git checkout |
| `couchloom` | `/home/dungxbuif/workspace/projects/couchloom/` | `git@github.com:dungxbuif/couchloom.git` | Git checkout |
| `db-management` | `/home/dungxbuif/workspace/projects/db-management/` | `ssh://git@gitlab.dungxbuif.com:2222/dungxbuif/db-management.git` | NestJS/Bun database operations UI, adapter-based backups and Drive upload; project/runtime map in [the 2026-10-26 reference](./deployments/2026-10-26-db-management-project-and-homelab-reference.md) and acceptance gates in [the production gate matrix](./deployments/2026-10-26-db-management-production-gates.md) |
| `datcom-clone` | `/home/dungxbuif/workspace/projects/datcom-clone/` | `git@github.com:dungxbuif/komu-foward.git` | Git checkout |
| `devtool` | `/home/dungxbuif/workspace/projects/devtool/` | none recorded | Git checkout without origin |
| `doino` | `/home/dungxbuif/workspace/projects/doino/` | `git@github-dungxbuif:dungxbuif/mezon-doino.git` | Git checkout |
| `donation` | `/home/dungxbuif/workspace/projects/donation/` | `git@github.com:dungxbuif/donate.git` | Git checkout |
| `fox-spirit` | `/home/dungxbuif/workspace/projects/fox-spirit/` | none recorded | Local directory |
| `go-study` | `/home/dungxbuif/workspace/projects/go-study/` | `git@github.com:dungxbuif/go-study.git` | Git checkout |
| `harness` | `/home/dungxbuif/workspace/projects/harness/` | `git@github.com:dungxbuif/harness.git` | Git checkout |
| `homelab-ops` | `/home/dungxbuif/workspace/projects/homelab-ops/` | `ssh://gitlab.dungxbuif.com:2222/dungxbuif/homelab-ops.git` | Canonical checkout; migration merged to local `main`; branch worktree retained at `/home/dungxbuif/workspace/homelab-ops-task1/` |
| `homelab-legacy` | `/home/dungxbuif/workspace/projects/homelab-legacy/` | none | Retained source snapshot; rollback/migration history only, never the deployment source |
| `homelab-tunnel` | `/home/dungxbuif/workspace/projects/homelab-tunnel/` | none recorded | Local directory |
| `homepage` | `/home/dungxbuif/workspace/projects/homepage/` | `ssh://gitlab.dungxbuif.com:2222/dungxbuif/homepage.git` | Git checkout |
| `k8s-syntax` | `/home/dungxbuif/workspace/projects/k8s-syntax/` | `git@github.com:dungxbuif/k8s-syntax.git` | Git checkout |
| `learn` | `/home/dungxbuif/workspace/projects/learn/` | none recorded | Git checkout without origin |
| `llm-flashcard` | `/home/dungxbuif/workspace/projects/llm-flashcard/` | `git@github.com:dungxbuif/llm-flashcard.git` | Git checkout |
| `mac-ocr` | `/home/dungxbuif/workspace/projects/mac-ocr/` | `git@github.com:dungxbuif/mac-ocr.git` | Git checkout |
| `mezon-desktop` | `/home/dungxbuif/workspace/projects/mezon-desktop/` | `git@github.com:dungxbuif/mezon-desktop.git` | Git checkout |
| `mezon-sdk-go` | `/home/dungxbuif/workspace/projects/mezon-sdk-go/` | `git@github.com:dungxbuif/mezon-sdk-go.git` | Git checkout |
| `mezonhook` | `/home/dungxbuif/workspace/projects/mezonhook/` | `git@github.com:dungxbuif/mezonhook.git` | Git checkout |
| `my-cv` | `/home/dungxbuif/workspace/projects/my-cv/` | `git@github.com:dungxbuif/my-cv.git` | Git checkout |
| `my_family_tree` | `/home/dungxbuif/workspace/projects/my_family_tree/` | `git@github.com:dungxbuif/my_family_tree.git` | Git checkout |
| `n8n-nodes-mezon` | `/home/dungxbuif/workspace/projects/n8n-nodes-mezon/` | none | Local package directory; no Git metadata |
| `project-learn` | `/home/dungxbuif/workspace/projects/project-learn/` | none recorded | Local directory |
| `random-template-code` | `/home/dungxbuif/workspace/projects/random-template-code/` | `git@github.com:dungxbuif/random-template-code.git` | Git checkout |
| `selfhost` | `/home/dungxbuif/workspace/projects/selfhost/` | `git@github-dungxbuif:dungxbuif/selfhost.git` | Git checkout |
| `speedydd` | `/home/dungxbuif/workspace/projects/speedydd/` | none recorded | Local directory |
| `study` | `/home/dungxbuif/workspace/projects/study/` | none recorded | Local directory |
| `test-clone` | `/home/dungxbuif/workspace/projects/test-clone/` | none recorded | Local directory |
| `toeic` | `/home/dungxbuif/workspace/projects/toeic/` | none recorded | Local directory |

## Migration Note

On 2026-09-16, project source directories were moved out of
`/home/dungxbuif/workspace/vaults/homelab/projects/` and back to
`/home/dungxbuif/workspace/projects/`. This keeps Homelab focused on infrastructure
documentation while preserving local and remote references for future work.

On 2026-10-31, the untracked `obsidian-livesync` source checkout was moved to
the desktop Trash at the owner's request. No Homelab documentation, CouchDB
data, LiveSync runtime, or other project directory was removed; the source
checkout was not present as an inventory row before removal.

On 2026-10-31, the local `mezon`, `urbanx-sample`, and `harness-experimental`
checkouts were moved to the desktop Trash at the owner's request. The latter
was the local clone whose origin redirected to `repository-harness`; no local
folder named `repository-harness` existed. No runtime service, Mezon webhook,
or Homelab infrastructure was removed.

The inventory was reconciled against the filesystem on 2026-10-31: 46 real
project directories remain. The old compatibility symlink
`/home/dungxbuif/workspace/projects/mezon-go-sdk` points to a missing Mac path
and is intentionally excluded from the current-project table.
