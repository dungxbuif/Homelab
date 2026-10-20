---
type: Deployment Note
title: "Route catalog reconciliation"
description: "Restore a valid declarative catalog after the NetBird service-name migration"
date: 2026-10-20
status: deployed-and-verified
---

# Route catalog reconciliation

## Intended behavior

`automation/routes/catalog.yml` remains the source for generated Pi5 Traefik
routes. The NetBird routes must keep their current Swarm DNS names under the
route `backend` mapping:

- `tasks.netbird_netbird-server:80` for h2c and HTTP management traffic
- `tasks.netbird_netbird-dashboard:80` for the dashboard

The catalog must parse against the route schema and render without contacting
production. No DNS, Traefik reload, or service restart is part of the source
repair.

## Verification plan

1. Parse and render the catalog with the pinned automation execution
   environment.
2. Run route contract tests and compare the generated artifact with the
   checked-in generated file.
3. Only after the generated artifact is accepted, reconcile the Pi5 file
   provider and run LAN/public smoke checks.

## Result so far

The two NetBird backend URLs had been dedented outside their `backend` maps,
which made the catalog invalid YAML. The source indentation was repaired and
the generated artifact was regenerated. The catalog now renders 26 routers and
26 services; all 13 route-contract tests pass. The live Pi5 config also showed
that `sync-db` had a narrower path rule than the catalog, so the catalog now
contains separate `couchdb` and `sync-db` routes and the contract covers that
policy. The live `whiteboard` route was also added to the catalog. The
generated artifact then passed the publish and smoke-test gate below.

The catalog now supports an explicit `service_name` for routes that share a
Traefik backend. `sync-db` shares the `couchdb` service, while the two NetBird
routers preserve the live `netbird-server` and `netbird-server-h2c` service
names. The renderer rejects conflicting backends behind one service name.

## Deployment result

The generated file was installed atomically on Pi5 at
`/home/dungxbuif/edge/traefik/dynamic.yml` on 2026-10-20. Rollback copy:
`/home/dungxbuif/edge/traefik/dynamic.yml.bak-route-catalog-20261020T161409Z`.
Traefik stayed running and emitted no configuration error in the reload
window. Smoke checks returned `200` for Whiteboard, KubeKosh, NetBird, and
OpenClaw; `sync-db/` returned the expected CouchDB `401`, and an unapproved
`sync-db/_utils/` path returned `404`.
