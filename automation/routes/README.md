# Declarative edge routes

`catalog.yml` is the editable route catalog. The renderer produces a Traefik
file-provider artifact for the Pi5 edge. It does not contact hosts, reload
Traefik, or change DNS.

```bash
python3 automation/scripts/render-routes.py \
  --catalog automation/routes/catalog.yml \
  --output /tmp/pi5-traefik.generated.yml
automation/scripts/verify-routes.sh \
  --catalog automation/routes/catalog.yml \
  --output /tmp/pi5-traefik.generated.yml
```

Every route declares exposure, owner, backend kind, health path, and rollback
version. Raw PostgreSQL, Redis, PgBouncer, and backup endpoints are rejected.
The Mac address `10.10.0.6` is allowed only for the explicit `mac_exception`
backend used by the native LLM service. LAN routes automatically receive the
`lan-only` middleware.

The generated file must be validated and smoke-tested on Pi5 and through the
VPS Rathole path before it replaces `migration/traefik/dynamic.yml`. The
current file-provider configuration remains the rollback source until that
publish gate passes.
