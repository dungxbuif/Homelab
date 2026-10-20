---
type: Deployment Evidence
title: "PostgreSQL and CouchDB restore acceptance"
description: "Scratch restore verification for the latest shared databases snapshot"
timestamp: 2026-10-21T00:00:00+07:00
---

# PostgreSQL and CouchDB Restore Acceptance

## Evidence

| Field | Result |
| --- | --- |
| Source run | `databases-20261020-180001` |
| Restic snapshot | `45fc58a1c463cb5ec85a008007e26ee1f0e5376d40ee1f858d2afe50436762cb` |
| Restored payload | 38 files/directories, 6.456 GiB, 7:29 elapsed |
| Payload integrity | All entries in `checksums.sha256` passed |
| PostgreSQL sample | `bds_prod` restored with native `restore-database.py`; `SELECT 1` passed |
| CouchDB sample | `obsidian_vault` restored with native `restore-database.py`; `49,210` documents matched the manifest |
| Restore targets | Temporary PostgreSQL 17/pgvector and CouchDB 3.3.3 containers on VM100; no published ports |
| Cleanup | Scratch containers, image, payload directory and temporary logs removed; VM100 returned to 81% disk usage / 39.6 GB free |

The snapshot manifest covered 12 PostgreSQL system/active databases and 5
CouchDB databases. Retired `goclaw` and `omniscan` were absent as expected.
No production database, volume, network, Pi5 service or application was
changed.

## Limits

This is a representative native restore acceptance, not a full application
cutover rehearsal. It validates one PostgreSQL database and one CouchDB
database from the latest shared snapshot. The remaining B1 restore class is
RustFS; a monthly unattended drill is tracked separately as B8.
