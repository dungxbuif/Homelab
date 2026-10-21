---
type: Research
title: "CouchDB streaming backup to Restic"
description: "Design and source boundary for avoiding full CouchDB staging on VM100"
timestamp: 2026-10-21T00:00:00Z
---

# CouchDB streaming backup to Restic

## Why

The GET-only Pi5 proxy works, but a complete `homelab` export is too large to
stage on VM100's current root filesystem. The 3,000-document gzip probe reached
about 1.1 GiB at 83% disk usage before it was stopped. Increasing page size or
compression does not remove the need to hold the whole payload locally.

## Selected design

1. Query the existing private proxy from VM100.
2. Serialize one database as a gzip NDJSON stream to stdout.
3. Feed that stream directly to a Restic `--stdin` backup with a stable
   `--stdin-filename` and the existing class/run tags.
4. Store only small metadata, manifest and checksum records locally.
5. Restore the stream into a temporary file or pipe, then use the existing
   CouchDB restore helper and document-count gate.

The stream exporter and the opt-in Restic stdin wrapper are now source-tested.
The multi-artifact manifest, remote snapshot receipt and restore drill are not
implemented yet, so this remains an experimental boundary.
The scheduled `databases` class remains unchanged during this work.

## Non-negotiable gates

- A non-zero exporter or Restic exit must not create a success marker.
- A truncated gzip stream must be rejected before it can be considered a
  snapshot.
- The manifest must record database name, document count, security metadata,
  stream checksum and Restic snapshot ID.
- Restore must match the recorded document count in an isolated CouchDB target.
- The Pi5 proxy remains GET-only and no CouchDB admin credential moves to VM100.
- The current Pi5 backup path remains the rollback path until one complete
  `homelab` restore passes.

