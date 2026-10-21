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

The stream exporter, opt-in Restic stdin wrapper and experimental per-database
uploader now have source tests. The uploader records a stream checksum and
Restic snapshot ID without staging the payload. The multi-artifact restore
drill is not implemented yet, so this remains an experimental boundary.

For the isolated gate only, `BACKUP_STREAM_RESTIC_REPOSITORY` may select a
local Restic repository and `RESTIC_LOCAL_REPOSITORY_DIR` mounts it at
`/restic-repo` inside the pinned client. These variables are deliberately not
part of the scheduled environment and must never replace the Google Drive
repository in production.

## Live source gate

On 2026-10-21, VM100 streamed `obsidian_vault` through the private Pi5 proxy
with gzip to `/dev/null`. The exporter exited `0`, reported `49,210` documents
and page size `3,000`, and left only a small metadata file; the transferred
source files and metadata were removed after the check. No Google Drive upload,
production scheduler or database mutation occurred.
The scheduled `databases` class remains unchanged during this work.

An isolated Restic-local upload was then attempted with the same stream and a
scratch repository. It was stopped at the VM100 `85%` disk warning before a
snapshot receipt was produced. The scratch repository was only `28 KiB`; no
remote repository or production scheduler was touched. This is a deliberate
failed-safe gate, not a successful Restic/restore acceptance.

## Non-negotiable gates

- A non-zero exporter or Restic exit must not create a success marker.
- The stream exporter must honor `BACKUP_COUCHDB_MIN_FREE_BYTES` before each
  page even though it does not stage the document payload locally.
- A truncated gzip stream must be rejected before it can be considered a
  snapshot.
- The manifest must record database name, document count, security metadata,
  stream checksum and Restic snapshot ID.
- Restore must match the recorded document count in an isolated CouchDB target.
- The Pi5 proxy remains GET-only and no CouchDB admin credential moves to VM100.
- The current Pi5 backup path remains the rollback path until one complete
  `homelab` restore passes.

