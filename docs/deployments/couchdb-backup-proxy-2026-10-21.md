---
type: Deployment
title: "Private CouchDB backup proxy"
description: "Pi5-local GET-only proxy staged for the VM100 native backup comparison"
timestamp: 2026-10-21T00:00:00Z
---

# Private CouchDB backup proxy

## Purpose

CouchDB does not provide a true database-level read-only member role. The
backup path therefore uses a narrow Pi5-local proxy instead of putting CouchDB
admin credentials on VM100 or publishing CouchDB itself.

## Live topology

```text
VM100 backup client
  -> homelab-net
  -> 10.10.0.5:15984 (Pi5 LAN only)
  -> couchdb-backup-proxy:8080 on Pi5 proxy_net
  -> couchdb:5984 on Pi5
```

- Source restriction: VM100 only (`10.10.0.31/32`).
- Public ingress: none. Traefik, Rathole and public DNS are not involved.
- Allowed methods: `GET` and `HEAD` only.
- Allowed resources: database metadata/security and `_all_docs` for the
  explicitly configured backup database list.
- Runtime limit: `128 MiB`, `0.25 CPU`, read-only filesystem, non-root user,
  dropped capabilities and no-new-privileges.
- VM100 client image is pinned to the approved curl digest recorded in the
  backup README.

## Credential boundary

The VM100 file contains only `BACKUP_PROXY_TOKEN` at
`/etc/homelab-backup/secrets/couchdb-backup-proxy.env`. The proxy's upstream
credentials remain on Pi5. Do not print, copy into Git, or put either value in
public documentation.

## Verification evidence

The deployment was verified from VM100:

1. Valid bearer token returned a non-empty HTTP `200` response.
2. Invalid bearer token returned HTTP `401`.
3. The container was running as UID/GID `65532:65532` with zero restarts.
4. A large export probe was stopped before completion because the `homelab`
   database would take an extended time; it did not write CouchDB data or a
   production completion marker.

The exporter now requests 1,000 documents per page and keeps the existing
128 MiB response ceiling. A staged performance check returned a 1,000-document
page of about 13 MiB promptly; this changes throughput only, not the allowed
database paths or credential boundary.

This is a staged transport. The scheduled `databases` class still uses the
existing Pi5 export path until a complete export, manifest comparison and
isolated restore comparison pass.

## Rollback

On Pi5:

```bash
cd /ssd-data/infra
docker compose -f docker-compose.yml \
  -f couchdb/backup-proxy.compose.yml stop couchdb-backup-proxy
```

Stopping this proxy does not stop CouchDB and does not disable the current
production backup path.

## Cutover gate

Before enabling `BACKUP_COUCHDB_TRANSPORT=network-proxy` for the scheduled
class:

1. run a complete staged export;
2. compare manifest, database and document counts with the Pi5 export;
3. restore the staged payload into an isolated CouchDB target;
4. observe one scheduled cycle without failures; and
5. only then remove Pi5 Restic/Drive credentials as a separate approved step.
