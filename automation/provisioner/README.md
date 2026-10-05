# Homelab Provisioner

`homelab-provisioner` is a private Swarm service that provides the narrow
privileged boundary between Semaphore and the Pi5 data services.

## Security boundary

- Semaphore does not receive `/var/run/docker.sock`.
- The provisioner has no published port and is attached only to
  `homelab-net`.
- The API accepts only the fixed database request schema. Inline passwords,
  arbitrary SQL, arbitrary CouchDB request bodies, and secret values are
  rejected.
- A new PostgreSQL/CouchDB application credential is generated in memory and
  stored as a Docker Swarm secret named by `swarm:<secret-name>`.
- The response contains only engine, resource name, secret reference, and
  changed/idempotent status.
- The catalog is updated atomically only after native creation and a smoke
  test succeed.

## Deploy on Pi5

Run from the repository root on a machine with the Pi5 Docker context:

```bash
docker build -t homelab/provisioner:20261005 automation/provisioner
docker secret create homelab_provisioner_token - < /path/to/private/token
docker stack deploy -c automation/provisioner/stack.yml homelab-provisioner
```

The secret must be created only once. Never put its value in Git, Semaphore
survey variables, or a job argument. The stack must remain portless.

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
