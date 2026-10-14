# Homelab Provisioner

`homelab-provisioner` is a private Swarm service that provides the narrow
privileged boundary between Semaphore and the Pi5 data services.

## Security boundary

- Semaphore does not receive `/var/run/docker.sock`.
- The provisioner has no published port. It currently uses `homelab-control-net`
  for Semaphore and retains `homelab-net` for legacy connectivity pending audit.
- The API accepts only the fixed database request schema. Inline passwords,
  arbitrary SQL, arbitrary CouchDB request bodies, and secret values are
  rejected.
- A new PostgreSQL/CouchDB application credential is generated in memory and
  stored as a Docker Swarm secret named by `swarm:<secret-name>`.
- The response contains only engine, resource name, secret reference, and
  changed/idempotent status.
- The catalog is updated atomically only after native creation and a smoke
  test succeed.

## Pending concurrency release

Source now serializes complete provisioning operations with a persistent
`inventory.yaml.provision.lock`, acquired before reading the catalog. Concurrent
requests receive HTTP 409 and may be retried after the active operation ends.
The lock is separate from catalog registration's lock and is never deleted.
Native partial failures still preserve generated secrets for reconciliation;
this does not provide rollback across Docker, PostgreSQL and CouchDB.

This behavior is tested but not yet deployed. Live image remains
`homelab/provisioner:20261005`; publish and verify an immutable replacement
containing the new HTTP handler before updating both handler and mounted module.
See [release evidence](../../docs/deployments/provisioner-concurrency-2026-10-15.md).

## Deploy on Pi5

Run from the repository root on a machine with the Pi5 Docker context:

```bash
docker build -f automation/provisioner/Dockerfile -t homelab/provisioner:development .
docker secret create homelab_provisioner_token - < /path/to/private/token
docker stack deploy -c automation/provisioner/stack.yml homelab-provisioner
```

The secret must be created only once. Never put its value in Git, Semaphore
survey variables, or a job argument. The stack must remain portless.

The local command above is for isolated development only. Production release
uses GitLab `build:provisioner`, which tests AMD64 and publishes ARM64 under
`registry-gitlab.dungxbuif.com/dungxbuif/homelab-automation/provisioner` by commit
tag and digest. Build context is the repository root, restricted by the
Dockerfile-specific allowlist. The image includes the HTTP server and all four
Python dependency modules; production SCRIPTS_PATH must select
`/app/provisioner/scripts`. Keep the old image and environment for rollback.

## API smoke test

The request must be sent from a private network peer and use the token file:

```bash
curl -fsS http://homelab-provisioner_provisioner:8787/healthz
curl -fsS -X POST http://homelab-provisioner_provisioner:8787/v1/provision \
  -H "Authorization: Bearer $(cat /run/secrets/homelab_provisioner_token)" \
  -H 'Content-Type: application/json' \
  --data @backup/provision-request.example.yaml
```

The example request is staging-only. The real Semaphore template passes the
request fields as survey values and never accepts a password field.
