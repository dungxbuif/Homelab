---
type: Deployment Evidence
title: "RustFS native pull cutover"
description: "VM100 RustFS export over the private Swarm overlay"
timestamp: 2026-10-21T14:30:44+07:00
---

# RustFS Native Pull Cutover

RustFS backup export now runs on VM100 over `s3-net`; the Pi5/container path
remains the rollback mode. No public S3 port or host IP is used.

- Production image: `rustfs/rustfs:1.0.1`, restart count remained `0`.
- Credential: dedicated bucket-scoped read-only service account at
  `/etc/homelab-backup/secrets/rustfs-readonly.env`, `root:ubuntu 0640`.
- Client image: `amazon/aws-cli:2.17.60@sha256:6b7484ab4ad2f69ae1d3665c91df54e42ab9d2b307f24be08f3a0c59948b8cb9`.
- Native export: 7 buckets, 3,115 checksum entries, `COMPLETE` marker.
- Comparison: no missing key/size pair against the latest Pi5 export; one
  newer `mypocket` object was expected because the native run was later.
- Restore: scratch RustFS restored all 62 `mac-ocr` objects.
- Least privilege: write and delete probes were both denied.
- Official systemd run: `rustfs-20261021-142606`, snapshot
  `d8a444b2ebad0046ad40c72c5e4145be10e830bbf48c3482cc62066323c94d92`,
  `ExecMainStatus=0`, success marker present.

## Rollback

Remove `BACKUP_RUSTFS_TRANSPORT=network` from the VM100 runner environment and
restart only the next RustFS backup unit. The dispatcher then uses the Pi5
forced-command path. The prior runner environment backup is retained on VM100.

Disposable probe runs, scratch RustFS data, temporary credentials and
comparison manifests were removed after verification. The official Restic run
was retained for normal retention policy.
