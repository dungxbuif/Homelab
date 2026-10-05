# RustFS Online Backup

`run-rustfs-backup.sh` exports the approved bucket inventory through the
RustFS S3-compatible API while RustFS remains online. It does not read or
copy the live RustFS volume.

The output is complete only after it contains:

- one `bucket-metadata.json` and `manifest.json` per bucket;
- `rustfs-adapter.json` and a top-level `manifest.json`;
- `checksums.sha256` and `COMPLETE`.

The per-bucket restore helper syncs only object payloads. Backup control files
(`bucket-metadata.json` and `manifest.json`) are excluded from the target
bucket, then key/size coverage is compared with the source manifest.

Versioning metadata is recorded when RustFS exposes it. Enabling versioning is
a separate operator decision and is not performed by this backup job.

## Example

```bash
run-rustfs-backup.sh \
  /ssd-data/infra/backups/homelab \
  rustfs-YYYYMMDD-HHMM \
  /path/to/backup/inventory.yaml \
  /ssd-data/infra/backup/secrets/rustfs.env
```

Restore tests must use a new isolated bucket name and must delete only that
test bucket after verification. A stopped-volume `rsync` copy is break-glass
cold recovery, not the scheduled mechanism.
