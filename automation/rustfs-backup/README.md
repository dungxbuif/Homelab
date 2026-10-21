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

## Optional VM100 network transport

The default transport uses the inventory endpoint and the existing Pi5 Docker
network. The VM100 network mode is source-ready but **not currently enabled**:
the Pi5 RustFS container is on Pi5-local Docker networks and publishes no host
S3 port, so VM100 cannot reach `s3-net` directly. Before enabling this mode,
provision a private, source-restricted endpoint and a read-only key. Do not use
the public `storage.dungxbuif.com` route for backup traffic.

Once that endpoint has passed object-listing, manifest-parity and isolated
restore checks, VM100 may opt in with these runtime-only values:

```text
BACKUP_RUSTFS_TRANSPORT=network
BACKUP_RUSTFS_ENDPOINT=http://rustfs:9000
BACKUP_RUSTFS_NETWORK=s3-net
BACKUP_RUSTFS_CLIENT_IMAGE=amazon/aws-cli:2.17.60
RUSTFS_CREDENTIALS_FILE=/etc/homelab-backup/secrets/rustfs-readonly.env
```

Network mode fails closed if the endpoint, network, client image or credential
file is missing. It never publishes an S3 port or falls back to a host IP.
The RustFS key must be read-only and the Docker network must be reachable from
VM100; no production cutover is implied by setting source defaults. The
scheduled runner continues using the Pi5 transport until endpoint reachability,
manifest comparison and isolated restore acceptance are recorded.
