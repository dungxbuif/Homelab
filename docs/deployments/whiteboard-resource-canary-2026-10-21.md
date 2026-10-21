# Whiteboard resource canary

Date: 2026-10-21

The persistent Compose source `/opt/apps/whiteboard/docker-compose.prod.yml`
was updated with CPU limits. Existing memory limits, security settings,
networks, images, environment, and volumes were preserved. The deployment used
`--no-build`, so no image was rebuilt.

```text
backend:        1.00 vCPU / 1 GiB
feature-worker: 0.50 vCPU / 256 MiB
collab:         1.00 vCPU / 1 GiB
mcp:            1.00 vCPU / 2 GiB
frontend:       0.50 vCPU / 256 MiB
```

All five containers became healthy. `https://whiteboard.dungxbuif.com/` and
`/healthz` both returned HTTP 200. The pre-change Compose source is retained at
`/opt/apps/whiteboard/docker-compose.prod.yml.bak-resource-20261021`.
