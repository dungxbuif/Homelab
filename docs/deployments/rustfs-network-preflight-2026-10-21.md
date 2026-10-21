---
type: Deployment
title: "RustFS VM100 network preflight"
description: "Read-only verification of the private RustFS S3 path from VM100"
timestamp: 2026-10-21T00:00:00Z
---

# RustFS VM100 Network Preflight

## Result

The earlier audit conclusion that VM100 could not reach RustFS through
`s3-net` was too broad. The network itself is shared correctly:

- Pi5 `s3-net`: Docker `overlay`, Swarm scope, attachable, non-internal.
- VM100 `s3-net`: Docker `overlay`, Swarm scope, attachable, non-internal.
- From a disposable VM100 client on `s3-net`, `rustfs` resolved to the
  overlay address `10.0.31.2`.
- `GET http://rustfs:9000/` returned HTTP `403 Forbidden`, proving the S3 API
  endpoint is reachable and refusing unauthenticated access as expected.
- The test used a pinned curl image and did not write RustFS data, create a
  bucket, or change a container/network.

## Security boundary

RustFS remains internal to the overlay for backup traffic. The public
`storage.dungxbuif.com` route is not part of this path and must not be used by
the backup runner. No host port is required.

## Cutover result

A dedicated bucket-scoped read-only key is stored only on VM100. The native
pull covered all seven inventory buckets, the key/size comparison found no
missing object against the latest Pi5 run, and an isolated `mac-ocr` restore
verified 62 objects. The scheduled RustFS transport is now VM100 `s3-net`;
remove `BACKUP_RUSTFS_TRANSPORT=network` to roll back.

RustFS's built-in `readonly` policy does not include `s3:ListBucket`, so it is
not sufficient for this exporter without a bucket-scoped custom policy.

The enrollment procedure is documented in
[`rustfs-backup-key-enrollment-2026-10-21.md`](./rustfs-backup-key-enrollment-2026-10-21.md).
The production image is now `1.0.1`; the controlled upgrade is recorded in
[`rustfs-upgrade-2026-10-21.md`](./rustfs-upgrade-2026-10-21.md). The production
Admin API enrollment initially returned HTTP 400 for the documented body, so a
fresh key was created through the approved RustFS IAM enrollment path. The
scheduled transport now uses that key only through the private `s3-net` path.
