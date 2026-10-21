---
type: Deployment Evidence
title: "RustFS object restore acceptance"
description: "Scratch S3 restore verification for the latest RustFS backup"
timestamp: 2026-10-21T00:00:00+07:00
---

# RustFS Object Restore Acceptance

## Evidence

| Field | Result |
| --- | --- |
| Source run | `rustfs-20261020-210003` |
| Restic snapshot | `667cb32216c6417d1ab9d2b7a6b28d2839d04e5e5b672af8e87329d6b942942c` |
| Payload | 3,968 files/directories, 718.848 MiB |
| Payload integrity | All 3,114 `checksums.sha256` entries passed |
| Scratch engine | `rustfs/rustfs:1.0.0-rc.1`, internal `homelab-net`, no host ports |
| Bucket restore | `mac-ocr` -> `mac-ocr-restore-20261021` |
| Native restore check | `restore-bucket.py` passed; 62 objects and manifest key/size map matched |
| Cleanup | Scratch bucket/container/payload/images removed; VM100 returned to 82% disk usage / 37.4 GB free |

The restore copied only object payloads, excluding backup control metadata. No
production RustFS container, bucket, volume or Pi5 service was changed.

This acceptance used a disposable scratch image pinned at the time of the
drill. The production RustFS image was subsequently upgraded to `1.0.1`; this
does not invalidate the payload/checksum restore result. A fresh restore drill
after the upgrade remains a useful follow-up, but is not required for the
upgrade health gate because the production service was only recreated and its
data volume was not migrated.

## Repair discovered during acceptance

The deployed helper lived at `/opt/apps/homelab-backup/app/rustfs-backup/`,
while the source tree lives under `automation/rustfs-backup/`. Its import path
assumed only the source layout and failed before S3 access. The helper now
resolves either source or deployed layout; the fix is covered by
`backup/tests/test_rustfs_manifest.py` and was deployed with a timestamped
rollback copy on VM100.
