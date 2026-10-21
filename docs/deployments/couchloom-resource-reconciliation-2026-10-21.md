# CouchLoom resource reconciliation

Date: 2026-10-21

Runtime inspection found a documentation/source drift: the CouchLoom app was
already capped, but its PostgreSQL and Ollama dependencies had no live Docker
limits. The persistent Compose sources were reconciled and live limits applied
without restarting or recreating containers:

```text
couchloom-postgres: 1.00 vCPU / 2 GiB / memory-swap 2 GiB
couchloom-ollama:   2.00 vCPU / 4 GiB / memory-swap 4 GiB
```

The app, PostgreSQL and Ollama healthchecks remained healthy. Existing data
volumes were preserved. CouchLoom is an internal service and intentionally has
no public route; public 404 responses are expected.

Rollback copies are retained beside both Compose sources with the suffix
`bak-resource-20261021`.
