---
type: Deployment
title: "Native backup pull transport"
description: "Source contract for moving PostgreSQL and CouchDB export work from Pi5 to VM100"
timestamp: 2026-10-21T00:00:00Z
---

# Native backup pull transport

## Purpose

B9 requires VM100 to perform the data export over the existing private Docker
networks. The current adapter still uses `docker exec` against the Pi5
PostgreSQL and CouchDB containers, so moving only the Restic retention job is
not enough.

## Source contract

- The existing container transport remains the default and is unchanged.
- `BACKUP_POSTGRES_TRANSPORT=network` runs the PostgreSQL client image on
  `pg-net`, connecting to the declared `BACKUP_POSTGRES_HOST` and port with a
  dedicated `backup_ro` credential file. It never publishes a database port or
  uses a host IP.
- `BACKUP_COUCHDB_TRANSPORT=network` runs the curl client image on
  `homelab-net`, connecting to the Docker service name `couchdb`. It uses a
  dedicated read-only CouchDB credential file and never exposes port 5984.
- Client image, network, endpoint and credential-file settings are runtime
  inputs in `/etc/homelab-backup/runner.env`; they are not committed.
- The source transport refuses network mode when any required setting is
  absent. Existing Pi5 mode remains the rollback path.

## Rollout gate

This source change is not the cutover. Before enabling it on VM100:

1. create and verify the least-privilege PostgreSQL/CouchDB backup identities;
2. enroll the reviewed client image digests and root-owned credential files on
   VM100;
3. run one native pull beside the current Pi5 export and compare manifests,
   object/document counts and restore results for one week; and
4. only then disable Pi5 `databases`/`rustfs` export and remove its Restic and
   Drive secrets.

No production service is stopped by the source transport. No live runtime was
changed by this document or its implementation.

## Verification

The three native-transport contract tests pass, including private network and
file-backed credential assertions. Python compilation passes for both adapters
and the new tests. The full local backup suite still has unrelated workstation
baseline failures: macOS has no `flock`, the local interpreter lacks `jinja2`,
and two health fixtures expect the enrolled Pi runner/marker setup. Those
failures do not exercise the new transport path; the pinned automation
execution environment remains the authoritative full-suite environment.
