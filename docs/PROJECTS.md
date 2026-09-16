---
type: Reference
title: "Local Project Workspace Layout"
description: "Local source checkout layout for projects adjacent to Homelab operations"
timestamp: 2026-09-11T00:00:00+07:00
---

# Local Project Workspace Layout

The Homelab checkout is the local anchor for most active source projects:

```text
/Users/dungxbuif/workspace/homelab/projects/
```

This directory is intentionally gitignored by the Homelab infrastructure repo.
It contains independent project repositories and workspaces; do not commit their
source trees into Homelab.

## Explicit Exception

`MyPocket` stays outside the Homelab project aggregation while it is still in
active development:

```text
/Users/dungxbuif/workspace/MyPocket/
```

Do not move MyPocket into `homelab/projects/` unless the owner explicitly asks.
The preserved local development data is separate from deployment placement.
MyPocket production web/API/worker are on VM100 and use Pi5 PgBouncer/Redis
through Docker DNS; keeping this source checkout unmoved does not make the
Mac the current production host. Local dev container state was not audited
in the documentation-only 2026-09-16 pass.

## Current Project Inventory

As of 2026-09-11, these workspace items were moved from
`/Users/dungxbuif/workspace/` into `homelab/projects/`:

```text
99tech_code-challenge
BrowserBridge
Flotsam
GraphQL_Real-time-Digital-Auction-Hub
Knowledgebase
MezonDong
NoteVault
Obsidian Vault
PocketNode
QnOffice
RuntimeRoasters
bds-ngoctinh
code-challenge
cortex
datcom-clone
devtool
doino
donation
fox-spirit
go-study
goclaw
harness
harness-experimental
homelab-ops
homelab-tunnel
homepage
learn
mac-ocr
mezon
mezon-desktop
mezon-go-sdk
mezon-sdk-go
mezonhook
my-cv
my_family_tree
open-design
project-learn
random-template-code
selfhost
speedydd
study
test-clone
toeic
urbanx-sample
```

`mezon-go-sdk` is a compatibility symlink to:

```text
/Users/dungxbuif/workspace/homelab/projects/mezon-sdk-go
```

## Operational Notes

- Use `/Users/dungxbuif/workspace/homelab/projects/<name>/` for project source
  checkouts when building or inspecting Homelab-related apps.
- Keep service runtime data separate from source. Production/dev runtime data
  remains under `/Users/dungxbuif/production/` or the relevant VM host path.
- `mac-ocr` source is now at
  `/Users/dungxbuif/workspace/homelab/projects/mac-ocr/` and remains read-only
  for runtime behavior changes; apply behavior changes through deployment-time
  patches or service-specific build context instead.
