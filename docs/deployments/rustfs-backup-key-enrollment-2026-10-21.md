---
type: Deployment
title: "RustFS backup key enrollment"
description: "Least-privilege RustFS service account for the VM100 native pull"
timestamp: 2026-10-21T00:00:00Z
---

# RustFS Backup Key Enrollment

## Intended behavior

The VM100 RustFS exporter uses a dedicated service account over the private
Swarm overlay `s3-net`. It may list bucket contents and read current/versioned
objects for the approved backup inventory. It must not write, delete, change
bucket policy, or call RustFS administration APIs.

The built-in RustFS `readonly` policy is insufficient because it does not
include `s3:ListBucket` or `s3:ListBucketVersions`. Enrollment therefore uses
a custom bucket-scoped policy with only:

- `s3:GetBucketLocation`
- `s3:GetBucketVersioning`
- `s3:ListBucket`
- `s3:ListBucketVersions`
- `s3:GetObject`
- `s3:GetObjectVersion`

### Current image compatibility check

The live image is now `rustfs/rustfs:1.0.1`. The prior production image
`1.0.0-rc.1` returned HTTP `400 InvalidRequest` while unmarshalling the
documented service-account body. After the controlled upgrade, the first
production enrollment still returned HTTP 400, so a fresh bucket-scoped key
was enrolled through the approved RustFS IAM path and verified from VM100.
The root key is not used for backup.

Each action is limited to the inventory bucket ARN and its object ARN. The
credential is stored only on VM100 at
`/etc/homelab-backup/secrets/rustfs-readonly.env` with `root:ubuntu 0640`.
Because the exporter passes this file directly to the AWS CLI container, it
contains only `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`. It is not
written to Git, the Pi5 runner env, or browser storage.

## Enrollment and verification gate

1. Create the service account through RustFS's signed Admin API/Console using
   the existing root credential only on Pi5.
2. Transfer the generated pair over the existing SSH connection directly into
   the root-owned VM100 credential file; delete temporary Pi5 material.
3. Run `list-object-versions`, `get-bucket-versioning` and a bounded object
   read from a disposable VM100 AWS CLI container on `s3-net`.
4. Run one native RustFS export beside the current Pi5 export. Compare bucket
   coverage, object keys, sizes and hashes.
5. Run the isolated RustFS restore drill. Only after both checks pass may the
   scheduled class change from Pi5/container transport to network transport.

Rollback is deleting the VM100 credential file and restoring the prior
`BACKUP_RUSTFS_TRANSPORT=container` setting. No RustFS data or production
container is changed by the verification steps.
