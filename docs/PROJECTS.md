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
/home/dungxbuif/workspace/
```

Do not commit independent application source trees into the Homelab
infrastructure repository. Use this file as the map from Homelab documentation
to the source checkouts.

## Layout Policy

- Keep Homelab operations, diagnostics, and infrastructure docs in this repo.
- Keep independent project source repositories under `/home/dungxbuif/workspace/<project>/`.
- Keep remote origin links here when available.
- Leave projects with no recorded `origin` as local-only until a remote is added.
- `MyPocket` remains outside this inventory unless explicitly added later:
  `/Users/dungxbuif/workspace/MyPocket/`.

## Project Inventory

| Project | Local folder | Remote origin | Notes |
| --- | --- | --- | --- |
| `99tech_code-challenge` | `/Users/dungxbuif/workspace/99tech_code-challenge/` | `git@github.com:harrybui-dev/99tech_code-challenge.git` | Git checkout |
| `BrowserBridge` | `/Users/dungxbuif/workspace/BrowserBridge/` | `git@github.com:dungxbuif/browserbridge.git` | Git checkout |
| `Flotsam` | `/Users/dungxbuif/workspace/Flotsam/` | none recorded | Git checkout without origin |
| `GraphQL_Real-time-Digital-Auction-Hub` | `/Users/dungxbuif/workspace/GraphQL_Real-time-Digital-Auction-Hub/` | `git@github.com:dungxbuif/GraphQL_Real-time-Digital-Auction-Hub.git` | Git checkout |
| `Knowledgebase` | `/Users/dungxbuif/workspace/Knowledgebase/` | `git@github.com:dungxbuif/Knowledgebase.git` | Git checkout |
| `MezonDong` | `/Users/dungxbuif/workspace/MezonDong/` | none recorded | Local directory |
| `NoteVault` | `/Users/dungxbuif/workspace/NoteVault/` | none recorded | Local directory |
| `PocketNode` | `/Users/dungxbuif/workspace/PocketNode/` | `git@github.com:dungxbuif/PocketNode.git` | Git checkout |
| `QnOffice` | `/Users/dungxbuif/workspace/QnOffice/` | `git@github.com:tiennguyenvan-ncc/QnOffice.git` | Git checkout |
| `RuntimeRoasters` | `/Users/dungxbuif/workspace/RuntimeRoasters/` | `git@github.com:dungxbuif/RuntimeRoasters.git` | Git checkout |
| `bds-ngoctinh` | `/Users/dungxbuif/workspace/bds-ngoctinh/` | `git@github.com:dungxbuif/bds-ngoctinh.git` | Git checkout |
| `code-challenge` | `/Users/dungxbuif/workspace/code-challenge/` | `git@github.com:dungxbuif/code-challenge.git` | Git checkout |
| `cortex` | `/Users/dungxbuif/workspace/cortex/` | `git@github.com:dungxbuif/cortex.git` | Git checkout |
| `couchloom` | `/Users/dungxbuif/workspace/couchloom/` | `git@github.com:dungxbuif/couchloom.git` | Git checkout |
| `db-management` | `/home/dungxbuif/workspace/db-management/` | `ssh://git@gitlab.dungxbuif.com:2222/dungxbuif/db-management.git` | NestJS/Bun database operations UI, adapter-based backups and Drive upload; project/runtime map in [the 2026-10-26 reference](./deployments/2026-10-26-db-management-project-and-homelab-reference.md) and acceptance gates in [the production gate matrix](./deployments/2026-10-26-db-management-production-gates.md) |
| `datcom-clone` | `/Users/dungxbuif/workspace/datcom-clone/` | `git@github.com:dungxbuif/komu-foward.git` | Git checkout |
| `devtool` | `/Users/dungxbuif/workspace/devtool/` | none recorded | Git checkout without origin |
| `doino` | `/Users/dungxbuif/workspace/doino/` | `git@github-dungxbuif:dungxbuif/mezon-doino.git` | Git checkout |
| `donation` | `/Users/dungxbuif/workspace/donation/` | `git@github.com:dungxbuif/donate.git` | Git checkout |
| `fox-spirit` | `/Users/dungxbuif/workspace/fox-spirit/` | none recorded | Local directory |
| `go-study` | `/Users/dungxbuif/workspace/go-study/` | `git@github.com:dungxbuif/go-study.git` | Git checkout |
| `goclaw` | `/Users/dungxbuif/workspace/goclaw/` | `git@github.com:dungxbuif/goclaw.git` | Git checkout |
| `harness` | `/Users/dungxbuif/workspace/harness/` | `git@github.com:dungxbuif/harness.git` | Git checkout |
| `harness-experimental` | `/Users/dungxbuif/workspace/harness-experimental/` | `https://github.com/hoangnb24/harness-experimental.git` | Git checkout |
| `homelab-ops` | `/home/dungxbuif/workspace/homelab-ops/` | `ssh://gitlab.dungxbuif.com:2222/dungxbuif/homelab-ops.git` | Canonical checkout; migration branch worktree is `/home/dungxbuif/workspace/homelab-ops-task1/` |
| `homelab-tunnel` | `/Users/dungxbuif/workspace/vaults/homelab-tunnel/` | none recorded | Local directory |
| `homepage` | `/Users/dungxbuif/workspace/homepage/` | `ssh://gitlab.dungxbuif.com:2222/dungxbuif/homepage.git` | Git checkout |
| `learn` | `/Users/dungxbuif/workspace/learn/` | none recorded | Git checkout without origin |
| `mac-ocr` | `/Users/dungxbuif/workspace/mac-ocr/` | `git@github.com:dungxbuif/mac-ocr.git` | Git checkout |
| `mezon` | `/Users/dungxbuif/workspace/mezon/` | `https://github.com/mezonai/mezon.git` | Git checkout |
| `mezon-desktop` | `/Users/dungxbuif/workspace/mezon-desktop/` | `git@github.com:dungxbuif/mezon-desktop.git` | Git checkout |
| `mezon-go-sdk` | `/Users/dungxbuif/workspace/mezon-go-sdk/` | see `mezon-sdk-go` | Compatibility symlink |
| `mezon-sdk-go` | `/Users/dungxbuif/workspace/mezon-sdk-go/` | `git@github.com:dungxbuif/mezon-sdk-go.git` | Git checkout |
| `mezonhook` | `/Users/dungxbuif/workspace/mezonhook/` | `git@github.com:dungxbuif/mezonhook.git` | Git checkout |
| `my-cv` | `/Users/dungxbuif/workspace/my-cv/` | `git@github.com:dungxbuif/my-cv.git` | Git checkout |
| `my_family_tree` | `/Users/dungxbuif/workspace/my_family_tree/` | `git@github.com:dungxbuif/my_family_tree.git` | Git checkout |
| `open-design` | `/Users/dungxbuif/workspace/open-design/` | `https://github.com/nexu-io/open-design.git` | Git checkout |
| `project-learn` | `/Users/dungxbuif/workspace/project-learn/` | none recorded | Local directory |
| `random-template-code` | `/Users/dungxbuif/workspace/random-template-code/` | `git@github.com:dungxbuif/random-template-code.git` | Git checkout |
| `selfhost` | `/Users/dungxbuif/workspace/selfhost/` | `git@github-dungxbuif:dungxbuif/selfhost.git` | Git checkout |
| `speedydd` | `/Users/dungxbuif/workspace/speedydd/` | none recorded | Local directory |
| `study` | `/Users/dungxbuif/workspace/study/` | none recorded | Local directory |
| `test-clone` | `/Users/dungxbuif/workspace/test-clone/` | none recorded | Local directory |
| `toeic` | `/Users/dungxbuif/workspace/toeic/` | none recorded | Local directory |
| `urbanx-sample` | `/Users/dungxbuif/workspace/urbanx-sample/` | `https://github.com/daohainam/urbanx-sample.git` | Git checkout |

## Migration Note

On 2026-09-16, project source directories were moved out of
`/Users/dungxbuif/workspace/vaults/homelab/projects/` and back to
`/Users/dungxbuif/workspace/`. This keeps Homelab focused on infrastructure
documentation while preserving local and remote references for future work.
