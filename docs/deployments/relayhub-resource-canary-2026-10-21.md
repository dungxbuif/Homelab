# RelayHub resource canary

Date: 2026-10-21

## Change

The persistent Compose source at `/opt/apps/relayhub/prod/compose.yml` now
sets these limits for the stateless application containers:

```text
relayhub-api:    1.00 vCPU / 1 GiB
relayhub-worker: 1.00 vCPU / 1 GiB
```

The image, environment, networks, healthchecks, NATS, Redis, and PostgreSQL
connection were unchanged. NATS and Redis were recreated as Compose dependencies
during apply, but their named/anonymous data volumes were retained. They remain
uncapped until their own stateful workload measurements are available.

## Verification

- Compose config validation passed before and after the source replacement.
- API and worker containers are healthy with the expected CPU/memory limits.
- NATS and Redis are healthy.
- `https://relayhub.dungxbuif.com/readyz`: HTTP 200.
- `https://relayhub.dungxbuif.com/healthz`: HTTP 200.
- `https://relayhub.dungxbuif.com/docs/`: HTTP 200.
- NATS persistent volume `prod_relayhub-nats-data` remains present.

Rollback source copy: `/opt/apps/relayhub/prod/compose.yml.bak-resource-20261021`.
