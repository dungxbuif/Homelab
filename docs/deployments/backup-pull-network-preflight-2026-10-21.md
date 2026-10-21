# Backup pull network preflight

Date: 2026-10-21
Status: network gate passed; export cutover remains pending

## Evidence

From VM100, disposable `busybox:1.37` probes attached to the existing private
Docker overlays reached the data endpoints by service DNS:

| Network | Endpoint | Result |
|---|---|---|
| `pg-net` | `pgbouncer:6432` | TCP connect passed |
| `s3-net` | `rustfs:9000` | TCP connect passed |
| `homelab-net` | `couchdb:5984` | TCP connect passed |

Existing application containers also resolve `pgbouncer`, `rustfs`, and
`couchdb` through Docker DNS. No backup export, data write, credential change,
service restart, or public port was changed by this preflight.

## Decision

The private network path is ready for the B9 observation phase. The next step
is a controlled native export comparison using read-only backup credentials:
compare one week of PostgreSQL, RustFS, and CouchDB output with the current
Pi5-originated snapshots before disabling Pi5 export and removing its Restic
and Drive secrets.
