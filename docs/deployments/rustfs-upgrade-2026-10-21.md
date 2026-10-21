---
type: Deployment Evidence
title: "RustFS production image upgrade"
description: "Controlled RustFS image upgrade on Pi5 with rollback evidence"
timestamp: 2026-10-21T14:03:27+07:00
---

# RustFS Production Image Upgrade

## Change

The Pi5 `rustfs` service was upgraded from `rustfs/rustfs:1.0.0-rc.1` to
`rustfs/rustfs:1.0.1`. The change was limited to the RustFS service; no other
Compose service was recreated and no data volume was migrated or deleted.

## Safety and verification

- Compose source backup: `/ssd-data/infra/docker-compose.yml.bak-rustfs-upgrade-20261021-140327`
- Inspect backup: `/ssd-data/infra/rustfs.inspect.bak-20261021-140327.json`
- `docker compose config` passed before apply.
- The service is running `1.0.1` with restart count `0`.
- Existing volume mount and required networks were retained.
- VM100 reached `rustfs:9000` over private `s3-net` and received the expected
  unauthenticated HTTP `403`.
- Public S3/console routes continued to return unauthenticated `403`.
- Recent RustFS logs contained no panic, fatal, IAM, or error entries.

## Rollback

Restore the Compose source backup, run `docker compose config`, then recreate
only `rustfs` with the prior image. Keep the current data volume untouched and
verify the same private endpoint and public-route checks after rollback.

## Remaining work

The upgrade did not create a backup service account. Production IAM enrollment
still returns HTTP 400 even though the documented request succeeds in an
isolated `1.0.1` container. The scheduled backup transport therefore remains
unchanged until a bucket-scoped read-only key is enrolled and a manifest/restore
comparison passes.
