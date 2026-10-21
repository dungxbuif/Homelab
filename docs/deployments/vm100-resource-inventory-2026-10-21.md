# VM100 resource inventory closeout

Date: 2026-10-21

After the controlled resource wave, every running VM100 container has a
non-zero Docker CPU and memory limit. The remaining unbounded entries were
resolved as follows:

- CouchLoom PostgreSQL: `1 CPU/2 GiB`.
- CouchLoom Ollama: `2 CPU/4 GiB`.
- Knowledge Hub Search/SearXNG: `0.5 CPU/512 MiB`.
- BDS Cloudflare tunnel: removed as an orphan. No `bds-app` container,
  Swarm service, or `/opt/apps/bds` source existed, so the tunnel could only
  emit DNS failures for the missing origin. Its unused `bds-tunnel-net` was
  removed with it.

The final live inventory query returned no running container with either
`NanoCpus=0` or `Memory=0`. Existing persistent volumes were not deleted.

The former BDS tunnel token was embedded in the removed container command;
future BDS deployment must create a new tunnel credential through the secret
store rather than reuse that token.
