---
type: Reference
title: "Local Project Workspace Inventory"
description: "Summary-only project inventory for source checkouts kept outside the Homelab repo"
timestamp: 2026-10-26T00:00:00+07:00
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

## Project Inventory

| Project | Local folder | Remote origin | Notes |
| --- | --- | --- | --- |
| `99tech_code-challenge` | `/home/dungxbuif/workspace/projects/99tech_code-challenge/` | `git@github.com:harrybui-dev/99tech_code-challenge.git` | Git checkout |
| `BrowserBridge` | `/home/dungxbuif/workspace/projects/BrowserBridge/` | `git@github.com:dungxbuif/browserbridge.git` | Git checkout |
| `Flotsam` | `/home/dungxbuif/workspace/projects/Flotsam/` | none recorded | Git checkout without origin |
| `GraphQL_Real-time-Digital-Auction-Hub` | `/home/dungxbuif/workspace/projects/GraphQL_Real-time-Digital-Auction-Hub/` | `git@github.com:dungxbuif/GraphQL_Real-time-Digital-Auction-Hub.git` | Git checkout |
| `Knowledgebase` | `/home/dungxbuif/workspace/projects/Knowledgebase/` | `git@github.com:dungxbuif/Knowledgebase.git` | Git checkout |
| `MezonDong` | `/home/dungxbuif/workspace/projects/MezonDong/` | none recorded | Local directory |
| `NoteVault` | `/home/dungxbuif/workspace/projects/NoteVault/` | none recorded | Local directory |
| `PocketNode` | `/home/dungxbuif/workspace/projects/PocketNode/` | `git@github.com:dungxbuif/PocketNode.git` | Git checkout |
| `QnOffice` | `/home/dungxbuif/workspace/projects/QnOffice/` | `git@github.com:tiennguyenvan-ncc/QnOffice.git` | Git checkout |
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
| `goclaw` | `/home/dungxbuif/workspace/projects/goclaw/` | `git@github.com:dungxbuif/goclaw.git` | Git checkout |
| `harness` | `/home/dungxbuif/workspace/projects/harness/` | `git@github.com:dungxbuif/harness.git` | Git checkout |
| `harness-experimental` | `/home/dungxbuif/workspace/projects/harness-experimental/` | `https://github.com/hoangnb24/harness-experimental.git` | Git checkout |
| `homelab-ops` | `/home/dungxbuif/workspace/projects/homelab-ops/` | `ssh://gitlab.dungxbuif.com:2222/dungxbuif/homelab-ops.git` | Canonical checkout; migration merged to local `main`; branch worktree retained at `/home/dungxbuif/workspace/homelab-ops-task1/` |
| `homelab-tunnel` | `/home/dungxbuif/workspace/projects/homelab-tunnel/` | none recorded | Local directory |
| `homepage` | `/home/dungxbuif/workspace/projects/homepage/` | `ssh://gitlab.dungxbuif.com:2222/dungxbuif/homepage.git` | Git checkout |
| `learn` | `/home/dungxbuif/workspace/projects/learn/` | none recorded | Git checkout without origin |
| `mac-ocr` | `/home/dungxbuif/workspace/projects/mac-ocr/` | `git@github.com:dungxbuif/mac-ocr.git` | Git checkout |
| `mezon` | `/home/dungxbuif/workspace/projects/mezon/` | `https://github.com/mezonai/mezon.git` | Git checkout |
| `mezon-desktop` | `/home/dungxbuif/workspace/projects/mezon-desktop/` | `git@github.com:dungxbuif/mezon-desktop.git` | Git checkout |
| `mezon-go-sdk` | `/home/dungxbuif/workspace/projects/mezon-go-sdk/` | see `mezon-sdk-go` | Compatibility symlink |
| `mezon-sdk-go` | `/home/dungxbuif/workspace/projects/mezon-sdk-go/` | `git@github.com:dungxbuif/mezon-sdk-go.git` | Git checkout |
| `mezonhook` | `/home/dungxbuif/workspace/projects/mezonhook/` | `git@github.com:dungxbuif/mezonhook.git` | Git checkout |
| `my-cv` | `/home/dungxbuif/workspace/projects/my-cv/` | `git@github.com:dungxbuif/my-cv.git` | Git checkout |
| `my_family_tree` | `/home/dungxbuif/workspace/projects/my_family_tree/` | `git@github.com:dungxbuif/my_family_tree.git` | Git checkout |
| `open-design` | `/home/dungxbuif/workspace/projects/open-design/` | `https://github.com/nexu-io/open-design.git` | Git checkout |
| `project-learn` | `/home/dungxbuif/workspace/projects/project-learn/` | none recorded | Local directory |
| `random-template-code` | `/home/dungxbuif/workspace/projects/random-template-code/` | `git@github.com:dungxbuif/random-template-code.git` | Git checkout |
| `selfhost` | `/home/dungxbuif/workspace/projects/selfhost/` | `git@github-dungxbuif:dungxbuif/selfhost.git` | Git checkout |
| `speedydd` | `/home/dungxbuif/workspace/projects/speedydd/` | none recorded | Local directory |
| `study` | `/home/dungxbuif/workspace/projects/study/` | none recorded | Local directory |
| `test-clone` | `/home/dungxbuif/workspace/projects/test-clone/` | none recorded | Local directory |
| `toeic` | `/home/dungxbuif/workspace/projects/toeic/` | none recorded | Local directory |
| `urbanx-sample` | `/home/dungxbuif/workspace/projects/urbanx-sample/` | `https://github.com/daohainam/urbanx-sample.git` | Git checkout |

## Migration Note

On 2026-09-16, project source directories were moved out of
`/home/dungxbuif/workspace/vaults/homelab/projects/` and back to
`/home/dungxbuif/workspace/projects/`. This keeps Homelab focused on infrastructure
documentation while preserving local and remote references for future work.
