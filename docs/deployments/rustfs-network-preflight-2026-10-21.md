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

## Remaining gate

Create a dedicated RustFS read-only service account/key with a custom policy
that grants `s3:GetBucketLocation`, `s3:ListBucket` and `s3:GetObject` only for
the inventory buckets. Store the resulting credential file only on VM100,
then run one native pull beside the current Pi5 export and compare manifests,
object counts and an isolated restore before changing the scheduled transport.

RustFS's built-in `readonly` policy does not include `s3:ListBucket`, so it is
not sufficient for this exporter without a bucket-scoped custom policy.

The enrollment procedure is documented in
[`rustfs-backup-key-enrollment-2026-10-21.md`](./rustfs-backup-key-enrollment-2026-10-21.md).
The current `1.0.0-rc.1` image's Admin API probe returned HTTP 400 for the
documented service-account body; no key was created and production was not
changed.
