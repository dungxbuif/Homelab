---
type: Deployment Evidence
title: "VM100 runtime resource audit"
description: "Read-only CPU, memory and configured Docker limit snapshot after backup/restore work"
timestamp: 2026-10-21T00:00:00+07:00
---

# VM100 Runtime Resource Audit

## Snapshot

The audit was read-only and ran on `vm100-prod` after the restore drill. The
host had 38 GB free and 81% filesystem usage at the end of the drill. No
container restart or resource mutation was performed.

| Workload | Observed RSS | Configured cap | Assessment |
| --- | ---: | ---: | --- |
| GitLab CE | 2.45 GiB | 10 GiB / 4 CPU | Keep current cap |
| KubeKosh | 967 MiB | 4 GiB / 2 CPU | Keep current cap; learning workload |
| Stirling PDF | 288 MiB | 2 GiB / 2 CPU | Keep current cap |
| n8n | 463 MiB | none | Add a measured cap in a manager window |
| OpenClaw | 334 MiB | none | Add a measured cap after model-load test |
| RelayHub API/worker | 22/20 MiB | none | Low priority cap, preserve burst headroom |
| MyPocket API/worker | 9/8 MiB | none | Add conservative cap with worker queue test |
| macOCR proxy | 16 MiB | none | Add cap after OCR concurrency benchmark |
| NetBird server/dashboard | 22/10 MiB | none | Small cap, verify gRPC/control-plane reconnect |
| CouchLoom PostgreSQL | 68 MiB | none | Do not cap before DB workload baseline |

The host sample showed no immediate memory pressure. The absence of a Docker
cap is still an isolation risk: a model load, OCR burst, workflow execution or
database compaction can consume host memory before the scheduler reacts.

## Action order

1. Capture peak samples during representative OpenClaw, OCR, MyPocket and n8n
   workloads.
2. Apply caps through the Swarm manager/Compose owner, one service at a time,
   using `start-first` only for stateless services and an explicit maintenance
   window for stateful ones.
3. Verify health, queue latency, model load, public routes and backup markers
   after each change. Roll back the individual service spec if any check fails.

This is evidence for the resource backlog, not permission to apply guessed
limits from a single idle snapshot.
